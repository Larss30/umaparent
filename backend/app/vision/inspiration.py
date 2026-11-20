"""Read the Inspiration tab of the Umamusume Details screen.

All positions are fractions of the screenshot width, so any phone resolution works.
Rows are found by their round radio icon (the layout repeats every 0.082 * width);
the row colour says blue / pink / green / white spark; stars are counted by gold pixels;
names are read by OCR and matched to data/skills.json.
"""
import os
import re
from concurrent.futures import ThreadPoolExecutor

import cv2
import numpy as np

from .imaging import to_hsv
from .match import match_spark
from .ocr import read_line

COL_X = {"L": 0.1926, "R": 0.5770}                  # left edge of each column
ICON_WIN = {"L": (0.203, 0.242), "R": (0.590, 0.629)}  # where the round icon sits
STAR0, STAR_STEP, STAR_HALF, STAR_DY = 0.1533, 0.0328, 0.011, 0.0275
NAME_X0, NAME_X1 = 0.050, 0.372
# Preprocessing settings tried in turn when a name is not matched confidently:
# (scale, threshold). Colored pills use (max saturation, min brightness) for white text.
GRAY_VARIANTS = [(3.0, 150), (4.0, 150), (3.0, 175), (4.0, 175)]
COLOR_VARIANTS = [(3.0, (80, 200)), (4.0, (80, 200)), (3.5, (70, 210)), (3.0, (100, 190))]
HEADER = re.compile(r"^\[(.+?)\]\s*(.+)$")


def locate(bgr: np.ndarray, hsv: np.ndarray) -> tuple[str, int]:
    """Which tab is open (skills / inspiration / career / unknown) and where the title bar ends."""
    H, W = bgr.shape[:2]
    m = cv2.inRange(hsv, (35, 110, 150), (55, 255, 255))
    m = cv2.morphologyEx(m, cv2.MORPH_CLOSE, np.ones((5, 5), np.uint8))
    n, _, st, _ = cv2.connectedComponentsWithStats(m)
    comps = [tuple(int(v) for v in s[:4]) for s in st[1:]]          # x, y, w, h
    bars = [c for c in comps if c[2] > 0.9 * W]
    if not bars:
        return "unknown", 0
    bar = min(bars, key=lambda c: c[1])
    bottom = bar[1] + bar[3]
    tabs = [c for c in comps if 0.25 * W < c[2] < 0.42 * W and 0.03 * W < c[3] < 0.09 * W and c[1] > bottom]
    if not tabs:
        return "unknown", bottom
    x, _, w, _ = tabs[0]
    cx = (x + w / 2) / W
    return ("skills" if cx < 0.33 else "inspiration" if cx < 0.67 else "career"), bottom


def _centers(mask: np.ndarray, W: int, x0: float, x1: float) -> list[int]:
    prof = (mask[:, int(x0 * W):int(x1 * W)] > 0).sum(1)
    thr, ys, y = 0.06 * (x1 - x0) * W, [], 0
    while y < len(prof):
        if prof[y] > thr:
            s = y
            while y < len(prof) and prof[y] > thr:
                y += 1
            if y - s > 0.012 * W:
                ys.append((s + y) // 2)
        else:
            y += 1
    return ys


def find_rows(hsv: np.ndarray, W: int, min_y: int) -> list[tuple[int, bool]]:
    """(y of the round icon, whether the right column has a spark in that row)"""
    m = cv2.inRange(hsv, (112, 30, 175), (135, 125, 255)) | cv2.inRange(hsv, (18, 120, 200), (30, 255, 255))
    left = [y for y in _centers(m, W, *ICON_WIN["L"]) if y > min_y]
    right = _centers(m, W, *ICON_WIN["R"])
    return [(y, any(abs(y - r) < 0.02 * W for r in right)) for y in left]


def row_kind(hsv: np.ndarray, W: int, side: str, yc: int) -> str:
    x, y = int((COL_X[side] + 0.352) * W), int(yc)
    h, s, _ = hsv[y - 3:y + 4, x - 3:x + 4].reshape(-1, 3).mean(0)
    if s < 45:
        return "gray"
    if 95 <= h <= 118:
        return "blue"
    if h >= 155 or h <= 4:
        return "pink"
    if 30 <= h <= 60:
        return "green"
    return "gray"


def read_stars(hsv: np.ndarray, W: int, side: str, yc: int) -> tuple[int, bool]:
    gold = cv2.inRange(hsv, (14, 110, 170), (32, 255, 255))
    r, cy, fr = int(STAR_HALF * W), yc + STAR_DY * W, []
    for i in range(3):
        cx = (COL_X[side] + STAR0 + STAR_STEP * i) * W
        win = gold[int(cy - r):int(cy + r), int(cx - r):int(cx + r)]
        fr.append(float(win.mean()) / 255 if win.size else 0.0)
    return sum(f > 0.22 for f in fr), any(0.07 < f < 0.30 for f in fr)


def _name_crop(bgr: np.ndarray, W: int, side: str, yc: int) -> np.ndarray:
    x0, x1 = int((COL_X[side] + NAME_X0) * W), int((COL_X[side] + NAME_X1) * W)
    return bgr[int(yc - 0.0215 * W):int(yc + 0.012 * W), x0:x1]


def _read_slot(bgr: np.ndarray, W: int, side: str, yc: int, kind: str) -> dict:
    """Read one row's name, re-reading with other settings until the match is confident."""
    crop, colored, best = _name_crop(bgr, W, side, yc), kind != "gray", None
    for scale, thr in (COLOR_VARIANTS if colored else GRAY_VARIANTS):
        cand = match_spark(kind if colored else "white", read_line(crop, colored, scale=scale, thr=thr)[0])
        if best is None or (cand["sure"], cand["score"]) > (best["sure"], best["score"]):
            best = cand
        if cand["sure"]:
            break
    return best


def _finish(cand: dict, stars: int, stars_unsure: bool) -> dict:
    out = {k: v for k, v in cand.items() if k not in ("sure", "score")}
    out["stars"] = max(1, stars)
    out["check"] = (not cand["sure"]) or stars_unsure or stars == 0 or not out["name"]
    return out


def read_header(bgr: np.ndarray, W: int, bottom: int) -> dict:
    """Best effort: '[Outfit] Name' from the title area."""
    crop = bgr[int(bottom + 0.035 * W):int(bottom + 0.125 * W), int(0.45 * W):int(0.80 * W)]
    if crop.size == 0:
        return {}
    text, conf = read_line(crop, False, psm=6)
    m = HEADER.match(text)
    return {"outfit": m.group(1).strip(), "name": m.group(2).strip()} if m and conf > 55 else {}


def read_inspiration(bgr: np.ndarray) -> dict:
    H, W = bgr.shape[:2]
    hsv = to_hsv(bgr)
    tab, bottom = locate(bgr, hsv)
    if tab != "inspiration":
        return {"kind": tab, "blocks": [], "header": {}, "rows": 0}
    rows = find_rows(hsv, W, bottom + int(0.1 * W))
    slots = []
    for yc, has_right in rows:
        for side in ("L", "R"):
            if side == "R" and not has_right:
                continue
            slots.append((side, yc, row_kind(hsv, W, side, yc)))
    with ThreadPoolExecutor(max_workers=min(4, os.cpu_count() or 2)) as pool:
        cands = list(pool.map(lambda s: _read_slot(bgr, W, s[0], s[1], s[2]), slots))
    blocks, cur = [], None
    for (side, yc, kind), cand in zip(slots, cands):
        stars, unsure = read_stars(hsv, W, side, yc)
        if side == "L" and kind == "blue":
            cur = {"anchored": True, "blue": None, "pink": None, "green": None, "whites": []}
            blocks.append(cur)
        elif cur is None:
            cur = {"anchored": False, "blue": None, "pink": None, "green": None, "whites": []}
            blocks.append(cur)
        sp = _finish(cand, stars, unsure)
        if kind in ("blue", "pink", "green"):
            cur[kind] = sp
        else:
            cur["whites"].append(sp)
    return {"kind": "inspiration", "blocks": blocks, "header": read_header(bgr, W, bottom), "rows": len(rows)}
