Editable config (YAML, loaded at startup):
- profiles/  one file per CM/LOH; copy aries-cup.yaml to add a new event
- ranks.yaml Parent Grade ladder
Still to come: races.yaml (G1 calendar) and affinity/ tables (Phase 4).
- styles/    one file per running style (tiered skill lists); _template.yaml to copy
- tiers.yaml   tier letters S..F plus Z (weight 0) and their default weights
- skills.json  searchable skill list: {"id": <game skill id or null>, "name", "type": skill|race|scenario|unique}.
               IDs are null until imported from a verified Global source; the app uses them once present.
