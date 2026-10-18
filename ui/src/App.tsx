import { lazy, Suspense, useMemo, useState } from 'react'
import type { AlgorithmName, Scenario } from './api/models'
import { CompareTab } from './components/CompareTab'
import { ControlsPanel } from './components/ControlsPanel'
import { ErrorNote, Panel, Spinner } from './components/Panel'
import { useAllocate } from './hooks/useAllocate'
import { useDebounced } from './hooks/useDebounced'
import { useMeta } from './hooks/useMeta'
import { useScenario } from './hooks/useScenario'
import {
  ALGORITHMS,
  type Controls,
  DEFAULT_CONTROLS,
  type EditMode,
  type Tab,
  toConfig,
  toGenerateRequest,
} from './lib/controls'
import { createMapSync } from './lib/mapSync'
import { addEngineer, deleteTicket } from './lib/scenarioEdits'

const HowItWorks = lazy(() => import('./components/how/HowItWorks'))
const ExperimentTab = lazy(() => import('./components/ExperimentTab'))

const TABS: { id: Tab; label: string }[] = [
  { id: 'compare', label: 'Compare' },
  { id: 'how', label: 'How it works' },
  { id: 'experiment', label: 'Experiment' },
]

interface Edits {
  base: Scenario
  scenario: Scenario
}

export default function App() {
  const meta = useMeta()
  const [tab, setTab] = useState<Tab>('compare')
  const [controls, setControls] = useState<Controls>(DEFAULT_CONTROLS)
  const [edits, setEdits] = useState<Edits | null>(null)
  const [selectedTicketId, setSelectedTicketId] = useState<string | null>(null)
  const [editMode, setEditMode] = useState<EditMode>('none')
  const [sync] = useState(createMapSync)

  const { seed, numEngineers, numTickets, weights, maxDistanceKm, speedKmph, estimator } = controls
  const generateRequest = useMemo(
    () => toGenerateRequest({ ...DEFAULT_CONTROLS, seed, numEngineers, numTickets }),
    [seed, numEngineers, numTickets],
  )
  const config = useMemo(
    () => toConfig({ ...DEFAULT_CONTROLS, weights, maxDistanceKm, speedKmph, estimator }),
    [weights, maxDistanceKm, speedKmph, estimator],
  )
  const debouncedRequest = useDebounced(generateRequest, 250)
  const debouncedConfig = useDebounced(config, 250)

  const scenarioQuery = useScenario(debouncedRequest)
  const base = scenarioQuery.data
  // Local edits apply to the scenario they were made on; a new seed or count starts clean.
  const scenario = edits && edits.base === base ? edits.scenario : base

  const allocation = useAllocate({
    scenario,
    config: debouncedConfig,
    algorithms: ALGORITHMS,
    enabled: meta.isSuccess,
  })
  const results = allocation.data?.results ?? {}

  const updateControls = (patch: Partial<Controls>) => {
    setControls((current) => ({ ...current, ...patch }))
    if ('seed' in patch || 'numEngineers' in patch || 'numTickets' in patch) {
      setEdits(null)
      setSelectedTicketId(null)
    }
  }

  const edit = (change: (current: Scenario) => Scenario) => {
    if (!base || !scenario) return
    setEdits({ base, scenario: change(scenario) })
  }

  const handleTicketClick = (ticketId: string) => {
    if (editMode === 'delete-ticket') {
      edit((current) => deleteTicket(current, ticketId))
      if (selectedTicketId === ticketId) setSelectedTicketId(null)
      return
    }
    setSelectedTicketId((current) => (current === ticketId ? null : ticketId))
  }

  const busy = scenarioQuery.isFetching || allocation.isFetching

  return (
    <div className="app">
      <header className="topbar">
        <div className="brand">
          <span className="logo" aria-hidden="true" />
          <div>
            <h1>Dispatch Engine</h1>
            <p>Engineers to fault tickets, three ways</p>
          </div>
        </div>
        <nav className="tabs" role="tablist" aria-label="Views">
          {TABS.map((t) => (
            <button
              key={t.id}
              type="button"
              role="tab"
              aria-selected={tab === t.id}
              className={tab === t.id ? 'tab active' : 'tab'}
              onClick={() => setTab(t.id)}
            >
              {t.label}
            </button>
          ))}
        </nav>
        <div className="api-status" data-testid="api-status">
          {meta.isSuccess ? (
            <>
              <span className="dot ok" /> API · storage {meta.data.storage} · cache {meta.data.cache}
            </>
          ) : meta.isError ? (
            <>
              <span className="dot bad" /> API offline
            </>
          ) : (
            <Spinner label="Connecting" />
          )}
        </div>
      </header>

      {meta.isError && (
        <div className="banner" role="alert">
          <ErrorNote error={meta.error} />
          <button type="button" onClick={() => void meta.refetch()}>
            Retry
          </button>
        </div>
      )}

      {tab !== 'experiment' && (
        <ControlsPanel
          controls={controls}
          meta={meta.data}
          onChange={updateControls}
          onRun={() => void allocation.refetch()}
          running={busy}
        />
      )}

      <main>
        {scenarioQuery.error ? <Panel title="Scenario" error={scenarioQuery.error} /> : null}
        {tab === 'compare' &&
          (scenario ? (
            <CompareTab
              scenario={scenario}
              results={results}
              algorithms={ALGORITHMS}
              left={controls.left}
              right={controls.right}
              onLeftChange={(left: AlgorithmName) => updateControls({ left })}
              onRightChange={(right: AlgorithmName) => updateControls({ right })}
              selectedTicketId={selectedTicketId}
              onSelectTicket={setSelectedTicketId}
              onTicketClick={handleTicketClick}
              onMapClick={(lat, lng) => edit((current) => addEngineer(current, lat, lng))}
              editMode={editMode}
              onEditModeChange={setEditMode}
              edited={scenario !== base}
              onResetEdits={() => setEdits(null)}
              sync={sync}
              loading={busy}
              error={allocation.error}
            />
          ) : (
            !scenarioQuery.error && (
              <Panel title="Loading scenario" loading>
                <p className="muted">Generating engineers and tickets…</p>
              </Panel>
            )
          ))}
        <Suspense
          fallback={
            <Panel title="Loading" loading>
              <p className="muted">Loading view…</p>
            </Panel>
          }
        >
          {tab === 'how' && scenario && (
            <HowItWorks
              scenario={scenario}
              config={debouncedConfig}
              left={controls.left}
              right={controls.right}
              onOpenExperiment={() => setTab('experiment')}
            />
          )}
          {tab === 'experiment' && <ExperimentTab config={debouncedConfig} meta={meta.data} />}
        </Suspense>
      </main>

      <footer className="footer">
        Synthetic data · road distance = straight line × 1.3 · 30 km/h · map © OpenStreetMap contributors
      </footer>
    </div>
  )
}
