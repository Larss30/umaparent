Editable config (YAML, loaded at startup):
- profiles/  one file per CM/LOH; copy aries-cup.yaml to add a new event
- ranks.yaml Parent Grade ladder
Still to come: races.yaml (G1 calendar) and affinity/ tables (Phase 4).
- styles/    one file per running style (tiered skill lists); _template.yaml to copy
- tiers.yaml   tier letters S..F plus Z (weight 0) and their default weights
- skills.json  searchable skill list: {"id": <game skill id or null>, "name", "type": skill|race|scenario|unique}.
               IDs are null until imported from a verified Global source; the app uses them once present.

skills.json provenance: built 2026-11-18 from a GameTora skill-list screenshot PDF (read by OCR, symbols
checked by eye). Normal skills are type skill, rainbow-pill skills are type unique. Gold and
negative skills are left out on purpose. Races and scenario sparks come from the sample parent
until the Phase 4 race list. IDs are null. Names with symbols are the most likely to hold typos.

skills.json "requires": optional list of requirement blocks; a skill can trigger if ANY block fits.
A block maps a condition (style, distance, surface, direction, course, season, weather, ground) to the
allowed values. Built from skill names (e.g. "Long Corners") and the description tags GameTora shows
(e.g. "(Pace/Late)", "(Pace, Long)", "(Dirt)"). Unique skills have no requirements. Conditions the
event or style doesn't define are treated as unknown and never block a skill.

Profiles tier their blue and pink sparks too (blue_tiers, pink_tiers); weights come from tiers.yaml.
- races.yaml     the 34 unique G1 races with year, half-month, surface and distance
- affinity.yaml  points per shared G1 win (community-sourced; edit if the game differs)

Standard distance: a race length that is a multiple of 400 m. skills.json requires {"standard": [...]} uses it; races without distance_m never block.
