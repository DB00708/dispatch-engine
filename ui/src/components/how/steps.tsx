import { useMemo, useState } from 'react'
import type { AllocationConfig, AllocationResult, Scenario, Trace } from '../../api/models'
import { algorithmLabel, plural } from '../../lib/format'
import { buildHeadline } from '../../lib/headline'
import type { EngineerState, MapLayers, MapLine } from '../../lib/mapLayers'
import { resultLayers } from '../../lib/mapLayers'
import { cellKey, costTerms, picksWithConflicts, violationText, type PickView } from '../../lib/trace'
import { MapView } from '../MapView'
import { MetricsChart } from '../MetricsChart'
import { CostGrid, type CellMark } from './CostGrid'

export function StepScenario({ scenario }: { scenario: Scenario }) {
  const layers = useMemo(() => resultLayers(scenario, undefined), [scenario])
  const count = (p: string) => scenario.tickets.filter((t) => t.priority === p).length
  const faults = ['electrical', 'mechanical', 'hydraulic', 'controls']
    .map((f) => `${scenario.tickets.filter((t) => t.fault_type === f).length} ${f}`)
    .join(', ')
  return (
    <div className="step-body">
      <div className="step-text">
        <p>
          <strong>{plural(scenario.engineers.length, 'engineer')}</strong> and{' '}
          <strong>{plural(scenario.tickets.length, 'ticket')}</strong> around Bengaluru: {count('P1')} P1, {count('P2')}{' '}
          P2 and {count('P3')} P3.
        </p>
        <p>Faults: {faults}.</p>
        <p className="muted">
          Seed {scenario.seed ?? 'custom'} makes the scenario repeatable: the same seed and counts always give the same
          engineers and tickets.
        </p>
      </div>
      <MapView name="how-scenario" scenario={scenario} layers={layers} height={360} />
    </div>
  )
}

interface StepFilterProps {
  scenario: Scenario
  trace: Trace
  config: AllocationConfig
  focusTicketId: string
  onFocus: (ticketId: string) => void
}

export function StepFilter({ scenario, trace, config, focusTicketId, onFocus }: StepFilterProps) {
  const i = trace.ticket_ids.indexOf(focusTicketId)
  const rows = trace.engineer_ids.map((engineerId, j) => {
    const codes = trace.violations_grid[i]?.[j] ?? []
    return {
      engineerId,
      j,
      km: trace.road_km_grid[i]?.[j] ?? 0,
      cost: trace.cost_grid[i]?.[j] ?? null,
      reasons: codes.map((code) => violationText(code, scenario, trace, config, i, j)),
    }
  })
  rows.sort((a, b) =>
    a.cost !== null && b.cost !== null ? a.cost - b.cost : a.cost !== null ? -1 : b.cost !== null ? 1 : a.km - b.km,
  )
  const allowed = rows.filter((r) => r.cost !== null)

  const layers: MapLayers = {
    lines: allowed.map(
      (r): MapLine => ({
        ticketId: focusTicketId,
        engineerId: r.engineerId,
        kind: 'candidate',
        tooltip: `${r.engineerId}: allowed, ${r.km.toFixed(1)} km`,
      }),
    ),
    engineerState: Object.fromEntries(
      rows.map((r) => [r.engineerId, (r.cost !== null ? 'feasible' : 'blocked') satisfies EngineerState]),
    ),
    unassigned: new Set(),
  }
  const notes = Object.fromEntries(rows.filter((r) => r.reasons.length).map((r) => [r.engineerId, r.reasons.join('; ')]))

  return (
    <div className="step-body">
      <div className="step-text">
        <label className="inline-field">
          Ticket{' '}
          <select value={focusTicketId} onChange={(event) => onFocus(event.target.value)} aria-label="Ticket to filter">
            {scenario.tickets.map((t) => (
              <option key={t.id} value={t.id}>
                {t.id} · {t.priority} · {t.fault_type}
              </option>
            ))}
          </select>
        </label>
        <p data-testid="filter-summary">
          <strong>
            {allowed.length} of {rows.length}
          </strong>{' '}
          engineers may take {focusTicketId}; {rows.length - allowed.length} break a hard rule. Click another ticket on
          the map to switch.
        </p>
        <ul className="filter-list" data-testid="filter-list">
          {rows.map((r) => (
            <li key={r.engineerId} className={r.cost !== null ? 'ok' : 'no'}>
              <strong>{r.engineerId}</strong>{' '}
              {r.cost !== null ? `allowed · ${r.km.toFixed(1)} km · cost ${r.cost.toFixed(2)}` : r.reasons.join('; ')}
            </li>
          ))}
        </ul>
      </div>
      <MapView
        name="how-filter"
        scenario={scenario}
        layers={layers}
        selectedTicketId={focusTicketId}
        focusTicketIds={new Set([focusTicketId])}
        engineerNotes={notes}
        onTicketClick={onFocus}
        height={420}
      />
    </div>
  )
}

export function StepCost({ trace, config }: { trace: Trace; config: AllocationConfig }) {
  const [hover, setHover] = useState<{ i: number; j: number } | null>(null)
  let readout = 'Hover a cell to see its distance and deadline-margin terms.'
  if (hover) {
    const cost = trace.cost_grid[hover.i][hover.j]
    const t = trace.ticket_ids[hover.i]
    const e = trace.engineer_ids[hover.j]
    if (cost === null) {
      readout = `${t} × ${e}: not allowed (${trace.violations_grid[hover.i][hover.j].join(', ')})`
    } else {
      const terms = costTerms(trace, config, hover.i, hover.j)
      readout = `${t} × ${e}: ${terms.roadKm.toFixed(1)} km, ${terms.slack} min spare → cost ${cost.toFixed(2)} = distance ${terms.distance.toFixed(2)} + margin ${terms.margin.toFixed(2)}`
    }
  }
  return (
    <div className="step-body single">
      <p>
        Every allowed pairing gets one number: weighted distance plus a penalty for a thin deadline margin. Leaving a
        ticket unserved costs 100 (P1), 30 (P2) or 10 (P3), so every algorithm drops a P3 before a P1.
      </p>
      <CostGrid trace={trace} testId="cost-grid" onHover={setHover} />
      <p className="readout" data-testid="cost-readout">
        {readout}
      </p>
    </div>
  )
}

interface StepAssignProps {
  scenario: Scenario
  left: AllocationResult
  right: AllocationResult
  pick: number
  onPick: (pick: number) => void
}

export function StepAssign({ scenario, left, right, pick, onPick }: StepAssignProps) {
  const trace = left.trace ?? right.trace
  const picks: PickView[] = useMemo(() => picksWithConflicts(left, right), [left, right])
  const shown = useMemo(() => picks.slice(0, pick), [picks, pick])
  const current = shown.at(-1)

  const leftMarks = new Map<string, CellMark>(
    shown.map((p, index) => [
      cellKey(p.ticketId, p.engineerId),
      {
        kind: p.grabbedFrom ? 'grabbed' : index === shown.length - 1 ? 'current' : 'pick',
        label: String(p.step),
      },
    ]),
  )
  const rightMarks = new Map<string, CellMark>(
    right.assignments.map((a) => [cellKey(a.ticket_id, a.engineer_id), { kind: 'chosen', label: '●' }]),
  )

  const layers = useMemo<MapLayers>(() => {
    const base = resultLayers(scenario, right)
    const ghost: MapLine[] = shown.map((p) => ({ ticketId: p.ticketId, engineerId: p.engineerId, kind: 'ghost' }))
    return { ...base, lines: [...base.lines, ...ghost] }
  }, [scenario, right, shown])

  if (!trace) return null
  const leftName = algorithmLabel(left.algorithm)
  const rightName = algorithmLabel(right.algorithm)
  return (
    <div className="step-body single">
      <div className="pick-controls">
        <button type="button" className="ghost" onClick={() => onPick(Math.max(0, pick - 1))} disabled={pick === 0}>
          ◀ Prev
        </button>
        <input
          type="range"
          min={0}
          max={picks.length}
          value={pick}
          onChange={(event) => onPick(Number(event.target.value))}
          aria-label="Pick step"
        />
        <button
          type="button"
          className="ghost"
          onClick={() => onPick(Math.min(picks.length, pick + 1))}
          disabled={pick >= picks.length}
        >
          Next ▶
        </button>
        <span className="muted" data-testid="pick-counter">
          {leftName} pick {pick} of {picks.length}
        </span>
      </div>
      <p className="readout" data-testid="pick-readout">
        {current
          ? `${leftName} pick ${current.step}: ${current.engineerId} → ${current.ticketId}` +
            (current.cost !== null ? ` (cost ${current.cost.toFixed(2)})` : '') +
            (current.grabbedFrom
              ? `. ${rightName} gives ${current.engineerId} to ${current.grabbedFrom} instead: an early grab another ticket needed.`
              : '.')
          : `${leftName} commits one cell at a time; ${rightName} looks at the whole grid and lights up its best set at once.`}
      </p>
      <div className="assign-grids">
        <CostGrid
          trace={trace}
          marks={leftMarks}
          compact
          testId="assign-grid-left"
          caption={`${leftName}: picks in order (orange = engineer ${rightName} used elsewhere)`}
        />
        <CostGrid
          trace={trace}
          marks={rightMarks}
          compact
          testId="assign-grid-right"
          caption={`${rightName}: whole best set at once`}
        />
      </div>
      <p className="muted small">
        Map: solid lines are {rightName}; dashed lines are {leftName}&apos;s picks so far.
      </p>
      <MapView name="how-assign" scenario={scenario} layers={layers} height={380} />
    </div>
  )
}

interface StepReportProps {
  left: AllocationResult
  right: AllocationResult
  onOpenExperiment: () => void
}

export function StepReport({ left, right, onOpenExperiment }: StepReportProps) {
  const headline = buildHeadline(left, right)
  const results = { [left.algorithm]: left, [right.algorithm]: right }
  const algorithms = left.algorithm === right.algorithm ? [left.algorithm] : [left.algorithm, right.algorithm]
  return (
    <div className="step-body single">
      <p className="report-headline">
        <strong>{headline.title}:</strong> {headline.detail}
      </p>
      <MetricsChart results={results} algorithms={algorithms} />
      <p>
        One scenario is an anecdote. The Experiment tab repeats this comparison across many seeded scenarios and
        engineer-to-ticket ratios and plots the gap.
      </p>
      <button type="button" className="primary" onClick={onOpenExperiment}>
        Open the Experiment tab
      </button>
    </div>
  )
}
