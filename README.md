# UmaParent (unofficial fan tool)

Scores Umamusume parents from inspiration sparks, per Champions Meeting / League of Heroes,
with affinity from G1 wins. Screenshot upload + manual entry share one editable review form.

## Run locally
    cp .env.example .env      # set a real password
    docker compose up --build
    curl localhost:8000/health
    curl localhost:8000/health/db
    open http://localhost:8000  (the web UI)

## Test / lint
    cd backend && pip install -r requirements-dev.txt && ruff check . && pytest

## Web UI features
Searchable skill fields (datalist over data/skills.json), per-event tiered checklists with
parent/grandparent presence icons, one tier board for skills, stats, aptitudes and green sparks (renamable tiers), tabs per parent/grandparent, white sparks in Skills/Races/Scenario columns, gold highlights,
JSON import/export, and a Skill tiers board (custom weights, stored in the browser, sent as
`custom_weights` when scoring).

## Screenshot reader
`POST /api/read-screenshots` takes 1-8 Inspiration-tab screenshots in scroll order and returns a parent
in the same JSON shape as import/export, with `check: true` on sparks it was unsure about. It runs on the
server with OpenCV and Tesseract (no AI service, no per-image cost). Rows are found by their round icon,
colour gives the spark type, stars are counted by gold pixels, and names are matched to data/skills.json.
Screenshots are read in memory and not stored. Code: backend/app/vision/.

## Roadmap
1. Scaffold, Docker Compose, CI  (done)
2. Scoring engine, YAML profiles, rank ladder  <- you are here
3. Frontend, anonymous sessions, login, saved parents
4. Affinity + G1 race-slot picker
5. Screenshot pipeline (classify, parse, dedupe, merge)
6. Deploy behind Cloudflare (Turnstile, rate limits), monitoring, backups

## Planned data model
users, parents (owner, character, outfit, stats, aptitudes),
styles live in data/styles/*.yaml (parent.style picks one)
spark_blocks (parent_id, role = self | grandparent_1 | grandparent_2, character),
sparks (block_id, type = blue|pink|green|white, name, stars),
g1_wins (parent_id, race, year_class, half_month).
