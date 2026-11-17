def grade_for(score: float, ranks: dict) -> str:
    """Highest grade whose threshold the score reaches. Scores are not capped."""
    best = ranks["grades"][0]["grade"]
    for g in ranks["grades"]:
        if score >= g["min"]:
            best = g["grade"]
    return best


def next_grade(score: float, ranks: dict) -> dict | None:
    for g in ranks["grades"]:
        if g["min"] > score:
            return {"grade": g["grade"], "at": g["min"], "needed": round(g["min"] - score, 1)}
    return None
