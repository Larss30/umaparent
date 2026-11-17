# UmaParent (unofficial fan tool)

Scores Umamusume parents from inspiration sparks, per Champions Meeting / League of Heroes,
with affinity from G1 wins. Screenshot upload + manual entry share one editable review form.

## Run locally
    cp .env.example .env      # set a real password
    docker compose up --build
    curl localhost:8000/health
    curl localhost:8000/health/db

## Test / lint
    cd backend && pip install -r requirements-dev.txt && ruff check . && pytest

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
