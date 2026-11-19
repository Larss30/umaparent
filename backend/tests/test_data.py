from app.scoring.config import load_profiles, load_skills, load_styles, norm


def test_skill_names_are_unique_and_typed():
    skills = load_skills()
    names = [norm(s["name"]) for s in skills]
    assert len(names) == len(set(names))
    assert {s["type"] for s in skills} <= {"skill", "unique", "race", "scenario"}


def test_every_checklist_skill_exists_in_the_database():
    known = {norm(s["name"]) for s in load_skills()}
    lists = [s["tiers"] for s in load_styles().values()]
    lists += [p.get("tiers") or {} for p in load_profiles().values()]
    missing = {n for tiers in lists for names in tiers.values() for n in names if norm(n) not in known}
    assert not missing, f"not in data/skills.json: {sorted(missing)}"
