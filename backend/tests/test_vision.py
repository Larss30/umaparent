import shutil
from pathlib import Path

import pytest

from app.vision import ImageError, read_screenshots
from app.vision.match import match_skill, match_vocab
from app.vision.merge import merge

FIX = Path(__file__).parent / "fixtures"
needs_ocr = pytest.mark.skipif(shutil.which("tesseract") is None, reason="tesseract is not installed")
WHITE = {"skill", "race", "scenario"}


def shot(name):
    return name, (FIX / name).read_bytes()


def head(block):
    return {s["kind"]: (s["name"], s["stars"]) for s in block["sparks"] if s["kind"] != "white"}


def whites(block):
    return {s["name"]: s["stars"] for s in block["sparks"] if s["kind"] == "white"}


def test_matcher_repairs_ocr_mistakes():
    assert match_skill("Nimble Navigatr", WHITE)["name"] == "Nimble Navigator"
    assert match_skill("Maverick O", WHITE)["name"] == "Maverick \u25cb"
    # Sparks are base-level skills, and Tesseract cannot tell the circle symbols apart, so always the one circle
    assert match_skill("Maverick \u00a9", WHITE)["name"] == "Maverick \u25cb"
    assert match_skill("Ignited Spirit: Speed +", WHITE)["category"] == "scenario"
    assert match_vocab("Dirt \u201c~E", ["Turf", "Dirt", "Sprint"]) == ("Dirt", True)


def test_matcher_ignores_punctuation_spacing_and_small_misreads():
    m = match_skill("Now We're Crutzen !", {"unique"})
    assert m["name"] == "Now We're Cruisin'!" and m["sure"] is True


def _result(whites):
    head = lambda k, n: {"kind": k, "name": n, "stars": 1, "check": False}  # noqa: E731
    return {"header": {}, "blocks": [{"anchored": True, "blue": head("blue", "Speed"),
            "pink": head("pink", "Turf"), "green": head("green", "Some Unique"), "whites": whites}]}


def test_merge_treats_a_misread_copy_as_the_same_spark():
    good = {"kind": "white", "name": "Uma Stan", "stars": 2, "category": "skill", "check": False}
    bad = {"kind": "white", "name": "Uma Stam", "stars": 2, "category": "skill", "check": True}
    out = merge([_result([good]), _result([bad])])
    assert [s["name"] for s in out["parent"]["blocks"][0]["sparks"] if s["kind"] == "white"] == ["Uma Stan"]


def test_unknown_names_are_flagged_not_dropped():
    m = match_skill("Totally Unknown Skill", WHITE)
    assert m["name"] == "Totally Unknown Skill" and m["sure"] is False


def test_not_an_image_is_rejected_clearly():
    with pytest.raises(ImageError, match="not a readable image"):
        read_screenshots([("x.png", b"definitely not an image")])


@needs_ocr
def test_career_tab_is_explained_not_misread():
    with pytest.raises(ImageError, match="Career Info"):
        read_screenshots([shot("career-info.png")])


@needs_ocr
def test_top_screenshot_reads_header_and_parent_block():
    res = read_screenshots([shot("inspiration-top.png")])
    assert res["parent"]["name"] == "Inari One" and res["parent"]["outfit"] == "Edomurasaki"
    block = res["parent"]["blocks"][0]
    assert head(block) == {"blue": ("Guts", 1), "pink": ("Dirt", 2), "green": ("Now We're Cruisin'!", 2)}
    w = whites(block)
    assert len(w) == 15 and w["Satsuki Sho"] == 1 and w["Nimble Navigator"] == 2 and w["Maverick \u25cb"] == 1


@needs_ocr
def test_full_screenshot_reads_parent_and_both_grandparents():
    res = read_screenshots([shot("inspiration-full.png")])
    roles = [b["role"] for b in res["parent"]["blocks"]]
    assert roles == ["self", "grandparent_1", "grandparent_2"]
    own, gp1, gp2 = res["parent"]["blocks"]
    assert head(gp1) == {"blue": ("Speed", 2), "pink": ("Turf", 2), "green": ("KEEP IT REAL.", 2)}
    assert head(gp2) == {"blue": ("Power", 2), "pink": ("Pace Chaser", 1), "green": ("Victoria por plancha \u2606", 2)}
    counts = (len(whites(own)), len(whites(gp1)), len(whites(gp2)))
    assert counts == (21, 17, 16), counts
    assert whites(gp2)["Pace Chaser Corners \u25cb"] == 3
    flagged = [s["name"] for b in res["parent"]["blocks"] for s in b["sparks"] if s["check"]]
    assert not flagged, flagged


@needs_ocr
def test_overlapping_screenshots_do_not_duplicate_sparks():
    res = read_screenshots([shot("inspiration-top.png"), shot("inspiration-full.png")])
    assert len(res["parent"]["blocks"]) == 3
    names = sorted(whites(res["parent"]["blocks"][0]))
    assert len(names) == 21, names
