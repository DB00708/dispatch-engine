# Dispatch Engine: Resource Allocation for Field Service

Assigns maintenance engineers in Bengaluru to equipment fault tickets, and compares three
allocation algorithms (Greedy, Hungarian, Regret) on the same input. Each one is shown on a
map, side by side, with plain-words reasons for every decision and a report card per algorithm.

**Stack:** FastAPI + NumPy/SciPy (`api/`) · React 18 + Vite + Leaflet/OpenStreetMap (`ui/`) ·
free and open source only, no API keys.

![Compare tab: Greedy and Hungarian on the same scenario](docs/screenshots/compare.png)

| How it works: Greedy's picks vs Hungarian's full set | Experiment: the scarcity sweep |
| --- | --- |
| ![How it works tab](docs/screenshots/how-it-works.png) | ![Experiment tab](docs/screenshots/experiment.png) |

## Quick start

**With Docker** (nothing else needed):

```bash
docker compose up --build -d      # then open http://localhost:8080
```

**Without Docker** (Python 3.11+ and Node 22.12+), in two terminals:

```bash
cd api && pip install -r requirements.txt && uvicorn app.main:app --reload    # API on :8000
cd ui && npm install && npm run dev                                           # UI on :5173
```

Optional Postgres (saved scenarios) and Redis (result cache):
`docker compose --env-file .env.db up --build -d`. Ports can be changed with `API_PORT` and
`WEB_PORT`.

## Check everything

```bash
./scripts/check-all.sh          # in-memory mode
./scripts/check-all.sh --db     # against Postgres + Redis
```

It runs every check in Docker and finishes with a pass/fail line per check:

| Check | What runs |
| --- | --- |
| API | ruff, strict mypy, 202 pytest unit/algorithm/API tests (warnings fail the run) |
| UI | ESLint (zero warnings), TypeScript, 21 Vitest tests, production build |
| API e2e | 11 tests against the running API, directly and through nginx |
| UI e2e | 12 Playwright tests in Chromium (any console error or warning fails) |
| Logs | no warnings or errors in any container |

## Approach

- **Domain:** engineers (location, shift, skills, experience) and fault tickets (location,
  fault type, priority P1–P3, deadline). One engineer does one ticket per dispatch round.
- **Hard rules:** skill match, inside the shift, before the deadline, within 30 km, one
  ticket per engineer.
- **Soft cost:** weighted distance plus a penalty for a thin deadline margin. Leaving a ticket
  unserved costs 100 / 30 / 10 for P1 / P2 / P3, so every algorithm drops a P3 before a P1.
- **Algorithms:** all three read one shared cost grid.
  - **Greedy:** the most urgent ticket takes its cheapest free engineer.
  - **Hungarian:** the optimal batch assignment, using one dummy "unassigned" column per ticket.
  - **Regret:** serves first the ticket that would lose most by waiting.
- **Explanations:** each assignment says why that engineer, and lists the runner-ups with
  "+4.2 km" or "lacks hydraulic skill". Each unserved ticket says why nobody could take it.
- **Metrics:** coverage, P1 coverage, km, deadline margin, tight jobs, objective, gap vs best,
  runtime. A separate validator re-checks every result against the raw scenario.

Details: [api/README.md](api/README.md) (engine, API contract, assumptions) and
[ui/README.md](ui/README.md) (screens, state, tests).

## What the comparison showed

Full write-up: [docs/algorithm-comparison.md](docs/algorithm-comparison.md).

- **Hungarian was never beaten** on the objective, in any test or sweep scenario, and it ran in
  about 0.1 ms.
- **Greedy's gap depends on scarcity.** In percent it peaks when engineers and tickets are
  balanced (+166% at a 1:1 ratio, because Hungarian's objective is small there). In absolute
  points it peaks at a ratio of 0.5, about one extra P2 ticket unserved per scenario.
- **Regret protects tickets with few options, not urgent ones.** Under scarcity its P1
  coverage falls to 64%, against 83% for Hungarian.
- **When each wins:** Greedy for a P1 that must go out the instant it arrives; Hungarian for
  batched dispatch rounds. Together: a rolling horizon.

## Assignment checklist

| Requirement | Where |
| --- | --- |
| Data model: resources, requests, assignments | [api/app/domain/models.py](api/app/domain/models.py), [api/app/api/schemas.py](api/app/api/schemas.py) |
| At least two strategies | Greedy, Hungarian, Regret in [api/app/engine/allocators/](api/app/engine/allocators) |
| Hard and soft constraints | [constraints.py](api/app/engine/constraints.py), [cost.py](api/app/engine/cost.py) |
| Decision explanations, metrics | [explain.py](api/app/engine/explain.py), [metrics.py](api/app/engine/metrics.py) |
| Tests with comparisons | [api/tests/](api/tests), [ui/e2e/](ui/e2e), `./scripts/check-all.sh` |
| Map, side-by-side comparison, metrics UI | Compare tab ([ui/src/components/](ui/src/components)) |
| Interactive features | Sliders, add engineer or delete ticket on the map, How it works replay, sweep |
| README and analysis | This file, [docs/algorithm-comparison.md](docs/algorithm-comparison.md) |
| Dependencies | [api/requirements.txt](api/requirements.txt), [ui/package.json](ui/package.json) |

## Layout

```
api/        FastAPI service: engine, allocators, tests (see api/README.md)
ui/         React app: Compare, How it works, Experiment (see ui/README.md)
docs/       algorithm write-up, sweep results, screenshots
scripts/    check-all.sh
docker-compose.yml   stack + test runners (api-tests, tools, e2e)
```

## With more time

- **ML duration estimator (p50/p90):** the `DurationEstimator` interface is already in place.
  Add a model class, and the API lists `ml`, the UI shows the toggle, and the engine uses
  p90 for the deadline check.
- **Multi-job routes per engineer:** vehicle routing with time windows (Google OR-Tools).
- **Real-time dispatch:** assign P1 tickets the moment they arrive, re-optimise the rest every
  few minutes.
- **Real travel times:** a self-hosted OSRM on OpenStreetMap data instead of straight line × 1.3.
