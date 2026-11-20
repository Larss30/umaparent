from .imaging import ImageError, decode
from .inspiration import read_inspiration
from .merge import merge

_TAB_HELP = {
    "skills": "shows the Skills tab. Open the Inspiration tab and screenshot that.",
    "career": "shows the Career Info tab (G1 wins are read by the race picker, coming next).",
    "unknown": "does not look like the Umamusume Details screen.",
}


def read_screenshots(files: list[tuple[str, bytes]]) -> dict:
    """files: [(filename, bytes)] in scroll order. Returns {'parent', 'notes', 'files'}."""
    results, per_file, notes = [], [], []
    for name, data in files:
        try:
            res = read_inspiration(decode(data))
        except ImageError as e:
            raise ImageError(f"{name}: {e}") from e
        if res["kind"] != "inspiration":
            notes.append(f"{name} {_TAB_HELP.get(res['kind'], _TAB_HELP['unknown'])}")
        else:
            results.append(res)
        per_file.append({"name": name, "kind": res["kind"], "rows": res["rows"]})
    if not results:
        raise ImageError(" ".join(notes) or "No spark rows found.")
    out = merge(results)
    out["notes"] = notes + out["notes"]
    out["files"] = per_file
    return out
