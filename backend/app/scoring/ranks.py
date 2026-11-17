def grade_for(score: float, ranks: dict) -> str:
    """Map a 0-100 score onto the grade ladder (evenly spaced, optional curve)."""
    grades = ranks["grades"]
    curve = ranks.get("curve", 1.0)
    n = len(grades)
    score = max(0.0, min(100.0, score))
    best = grades[0]
    for i, g in enumerate(grades):
        if 100.0 * (i / n) ** curve <= score:
            best = g
    return best
