# Dispatch Engine API

A field-service dispatcher for Bengaluru: it assigns maintenance engineers to equipment
fault tickets and compares three allocation algorithms (Greedy, Hungarian, Regret) on the
same input. Every decision comes with plain-words reasons, and every result with a report
card. FastAPI + NumPy/SciPy; the React UI lives in [`../ui`](../ui). For the whole project
(quick start, screenshots, one-command checks) see the [root README](../README.md).

- **Stateless:** the client sends the whole scenario with each call, so the same build runs
  locally, in Docker and on Cloud Run.
- **No required infrastructure:** in-memory storage and no cache by default. Postgres and
  Redis switch on with `STORAGE=postgres` and `CACHE=redis`.
- **Write-up:** [docs/algorithm-comparison.md](../docs/algorithm-comparison.md) (Hungarian is
  never beaten; with as many engineers as tickets, Greedy serves 7.5 percentage points fewer
  tickets).

## Quick start

**Local (Python 3.11+), from this `api/` folder**

```bash
python -m venv .venv
.venv/Scripts/activate        # Windows; use `source .venv/bin/activate` on macOS/Linux
pip install -r requirements-dev.txt
uvicorn app.main:app --reload
```

Open http://localhost:8000/docs for the interactive API.

**Docker**, from the repository root (starts the UI too):

```bash
docker compose up --build -d                       # API on :8000, UI on :8080, in-memory
docker compose --env-file .env.db up --build -d    # + Postgres (saved scenarios) and Redis (result cache)
```

If port 8000 is taken, set `API_PORT` (for example `API_PORT=8001`).

## API

All endpoints are JSON under `/api`. FastAPI serves the schema at `/openapi.json`, and the UI
generates its TypeScript types from it.

| Method | Path | Purpose |
| --- | --- | --- |
| GET | `/api/meta` | Algorithms, fault types, available estimators, defaults, limits |
| GET | `/api/health` | Liveness, plus which storage and cache are active |
| POST | `/api/scenarios/generate` | Seeded scenario (the same seed and counts always give the same scenario) |
| GET | `/api/scenarios/{id}` | A generated scenario, read back from storage |
| POST | `/api/allocate` | Run one or more algorithms on a scenario; `include_trace` adds the cost grid and pick order |
| POST | `/api/experiments/sweep` | Scarcity sweep across engineer-to-ticket ratios |

Example:

```bash
curl -s localhost:8000/api/scenarios/generate -H 'Content-Type: application/json' \
  -d '{"seed": 42, "num_engineers": 12, "num_tickets": 20}' > scenario.json
curl -s localhost:8000/api/allocate -H 'Content-Type: application/json' \
  -d "{\"scenario\": $(cat scenario.json), \"algorithms\": [\"greedy\", \"hungarian\"]}"
```

Every non-2xx response uses one envelope:

```json
{"error": {"code": "ESTIMATOR_UNAVAILABLE", "message": "ML estimator is not loaded; use 'naive'.", "details": {"requested": "ml"}}}
```

`VALIDATION_ERROR` (422) covers bad input, such as an unknown algorithm, counts over the
limits, a timestamp without an offset or duplicate ids. `ESTIMATOR_UNAVAILABLE` (400) means
`"estimator": "ml"` was requested, but this build ships no model. `SCENARIO_NOT_FOUND`,
`NOT_FOUND` and `METHOD_NOT_ALLOWED` cover the rest.

## How the engine decides

**Hard rules.** A pairing is either allowed or not:

| Code | Rule |
| --- | --- |
| `SKILL_MISMATCH` | The engineer has the ticket's fault type |
| `OFF_SHIFT` | The job starts and finishes inside the engineer's shift |
| `MISSES_DEADLINE` | It finishes before the ticket deadline |
| `TOO_FAR` | Road distance ≤ `max_distance_km` (default 30) |
| `ALREADY_ASSIGNED` | One ticket per engineer per round (enforced by each allocator, re-checked by the validator) |

Timing: `travel = road_km / speed × 60`, `start = max(dispatch + travel, shift_start)`,
`finish = start + duration_p90`, `slack = deadline − finish`.

**Soft cost** (lower is better):
`cost = w_distance × road_km / max_km + w_slack × (1 − min(slack / 120, 1))`, with weights
1.0 and 0.5 by default (adjustable per request). A blocked pairing costs `1e9`. Leaving a
ticket unserved costs 100 / 30 / 10 for P1 / P2 / P3. The **objective** is the sum of
pairing costs plus unserved penalties, and every result is scored on it.

**Allocators** all read one shared matrix that is built once per call:

- **Greedy:** sort by priority, then deadline; each ticket takes its cheapest free
  engineer.
- **Hungarian:** an n × (m + n) matrix with one dummy "unassigned" column per ticket,
  solved by `scipy.optimize.linear_sum_assignment`. It is optimal for the objective.
- **Regret:** repeatedly serve the ticket whose best and second-best options differ most,
  where "unassigned" also counts as an option.

**Explanations.** Each assignment has a summary (for example "2nd-nearest feasible
hydraulic-skilled engineer (closer E07 went to T03); finishes 94 min before the deadline")
and up to two runner-ups: feasible ones with "+4.2 km, +0.14 cost", blocked ones with
reasons such as "lacks hydraulic skill" or "would finish 25 min after deadline". Each
unserved ticket says why, for example "No mechanical-skilled engineer within 30 km
(nearest is 41.3 km)".

**Metrics per result:** assigned, coverage %, P1 coverage %, priority-weighted coverage,
total and average km, average deadline margin, tight assignments (< 15 min), utilisation,
objective, gap vs the best algorithm, unserved by priority, and runtime.

### Assumptions

| Assumption | Value | Where |
| --- | --- | --- |
| Road distance | Straight line × 1.3 | `ROAD_FACTOR` |
| Travel speed | 30 km/h | per request (`speed_kmph`) |
| Job duration (naive estimator) | electrical 75, mechanical 90, hydraulic 110, controls 60 min | `app/estimators/naive.py` |
| Comfortable deadline margin | 120 min | `app/engine/cost.py` |
| "Tight" assignment | < 15 min of slack | `TIGHT_SLACK_MIN` |
| Region | Bengaluru, lat 12.83–13.10, lng 77.47–77.76 | `app/data/generator.py` |

## Testing

```bash
pytest                                             # 202 unit, algorithm and API tests (warnings fail the run)
ruff check . && ruff format --check . && mypy      # lint, format, strict typing
E2E_BASE_URL=http://localhost:8000 pytest -m e2e   # 11 checks against a running API
python -m scripts.run_sweep                        # regenerate ../docs/algorithm-comparison-results.md
```

The same checks run in Docker with no local Python: `docker compose run --rm api-tests`
from the repository root.

- **Unit:** haversine against two independent formulas, one test per violation code,
  cost weights, generator determinism, and the storage LRU.
- **Algorithms:** the validator passes for all three allocators on 50 random seeds;
  Hungarian ≤ Greedy and ≤ Regret on the objective; the greedy trap; scarcity (one engineer,
  a P1 and a P3, so every algorithm serves the P1); zero engineers, zero tickets, no
  feasible pairs; determinism.
- **API:** the documented shape of every endpoint, the error envelope for 400, 404, 405,
  422 and 500, cache hit and miss headers, and CORS.
- **E2E (`-m e2e`):** generate → fetch from storage → allocate → re-validate every hard rule
  from the raw scenario. Set `E2E_EXPECT_STORAGE=postgres` and `E2E_EXPECT_CACHE=redis` to
  assert the backends.

## Configuration

All settings are environment variables with working defaults (see `.env.example`):
`STORAGE`, `CACHE`, `DATABASE_URL`, `REDIS_URL`, `CACHE_TTL_SECONDS`, `CORS_ORIGINS`,
`LOG_LEVEL`, `ROAD_FACTOR`, `MAX_ENGINEERS`, `MAX_TICKETS`, and `FRONTEND_DIST` (serve the
built UI from the API for a single-image deploy, for example on Cloud Run, which sets
`$PORT`).

## Layout

```
app/
  main.py, config.py
  api/        routes/, schemas.py (the contract), mappers.py, errors.py, deps.py
  domain/     models.py, geo.py, clock.py
  engine/     matrix.py, constraints.py, cost.py, allocators/, explain.py, metrics.py,
              validator.py, trace.py, runner.py, sweep.py
  estimators/ base.py (DurationEstimator protocol), naive.py
  data/       generator.py
  storage/    memory.py, postgres.py, cache.py
tests/        unit/, test_allocators.py, test_explain_metrics.py, test_api.py, e2e/
scripts/      run_sweep.py (writes ../docs/algorithm-comparison-results.md)
```

## Not built, and how it would plug in

- **ML duration estimator (p50/p90):** add a class that implements `DurationEstimator` and
  register it in `app/estimators/__init__.py`. `/api/meta` then lists `ml`, the UI shows the
  toggle, and the engine already uses p90 for the deadline check.
- **Multi-stop routes, real road networks, two-person jobs:** out of scope. See the
  write-up for the next steps.
