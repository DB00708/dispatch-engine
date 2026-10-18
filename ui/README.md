# Dispatch Engine UI

React front end for the [API in `../api`](../api). It answers one
question a reviewer can't ignore: with the same tickets and the same engineers, why did two
algorithms send people to different places?

- **Compare:** a headline in plain words ("Hungarian vs Greedy: +1 P1 ticket served,
  objective 46% lower"), two synced Leaflet maps, six metric chips per algorithm, a "Why?"
  panel for any ticket or line, and the full report card. Moving the Engineers slider
  regenerates the scenario live. You can add engineers or delete tickets on the map.
- **How it works:** replays one run as five steps (scenario, hard filter, cost grid, assign,
  report card), with Play or click-through. Step 4 shows Greedy committing one cell at a
  time while Hungarian lights up its whole best set.
- **Experiment:** the scarcity sweep behind the write-up, as charts, auto-written findings
  and a table.

React 18, Vite 8, TypeScript, TanStack Query, Leaflet + react-leaflet, Recharts.

## Run it

**Local dev (Node 22.12 or newer; `.nvmrc` pins 22).** Start the API on :8000 first (see
[api/README.md](../api/README.md)), then from this `ui/` folder:

```bash
nvm use                # optional: picks Node 22 from .nvmrc
npm install
npm run dev            # http://localhost:5173, proxies /api to VITE_API_PROXY (default :8000)
```

**Everything in Docker (no local Node needed),** from the repository root: `./run.sh`
(macOS/Linux) or `.\run.cmd` (Windows). It opens http://localhost:8080, or the next free port
if 8080 is taken. Add `--db` for Postgres + Redis.

nginx serves the built app and proxies `/api` and `/docs` to the API container, so the
browser only talks to one origin and only one port is published.

## Scripts

| Command | What it does |
| --- | --- |
| `npm run dev` | Vite dev server |
| `npm run lint` | ESLint, zero warnings allowed |
| `npm run typecheck` | `tsc -b` across app and tooling |
| `npm test` | Vitest unit tests |
| `npm run build` | Type-check and production build |
| `npm run check` | All of the above |
| `npm run test:e2e` | Playwright against `E2E_BASE_URL` (default http://localhost:8080) |
| `npm run screenshots` | Regenerate the README images in `../docs/screenshots` |
| `npm run gen:types` | Regenerate `src/api/types.ts` from the API's `/openapi.json` |

Without a local Node 22, run any of these in the toolbox container, from the repository root:

```bash
docker compose run --rm tools ci           # install into a Docker volume
docker compose run --rm tools run check    # lint + types + unit tests + build
```

## End-to-end tests

From the repository root:

```bash
docker compose up --build -d
docker compose run --rm e2e                # Playwright in mcr.microsoft.com/playwright, against the stack
```

12 scenarios cover:

- both maps drawn, fitted to the whole scenario and kept in sync
- explanations for a clicked ticket
- the Engineers slider regenerating the scenario
- editing the scenario on the map and resetting it
- all five How-it-works steps, including Play
- the sweep, and client-side validation of the sweep form
- an API error shown inline next to the failing panel
- markers still drawn with map tiles offline

Tile requests are stubbed, so the tests never need the internet. Any browser console error
or warning fails the test.

## How it talks to the API

- `src/api/types.ts` is generated from the API's OpenAPI schema, so the front end and back
  end can't drift. `src/api/models.ts` gives the generated types friendly names.
- The scenario lives in React state. Edits (add an engineer, delete a ticket) change it
  locally, and the whole scenario is sent with each allocate call.
- `meta` is fetched once and drives the algorithm list, limits and the estimator toggle.
  The toggle only renders when the API lists more than one estimator.
- Allocation is a pure function of its inputs, so it is a TanStack **query** keyed by
  scenario and config: returning to earlier inputs is instant, and the previous result stays
  on screen while the next one loads. The sweep runs on a button press, so it is a
  **mutation**.
- Each panel has its own spinner and shows the API's error-envelope message inline. One
  failing call never blanks the page.

## Layout

```
src/
  api/          client.ts (fetch + ApiError), types.ts (generated), models.ts
  hooks/        useMeta, useScenario, useAllocate, useSweep, useDebounced
  lib/          headline, format, mapLayers, mapSync, scenarioEdits, sweep, trace, controls
  components/   CompareTab, ComparisonGrid, MapView, MetricChips, HeadlineBanner,
                ExplanationPanel, MetricsTable, MetricsChart, ControlsPanel, Legend,
                ExperimentTab, SweepChart, Panel, how/ (HowItWorks, steps, CostGrid)
e2e/            app.spec.ts, screenshots.spec.ts
nginx/          default.conf.template
```
