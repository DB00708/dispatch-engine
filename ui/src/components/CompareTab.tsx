import type { AlgorithmName, Results, Scenario } from '../api/models'
import type { EditMode } from '../lib/controls'
import type { MapSync } from '../lib/mapSync'
import { ComparisonGrid } from './ComparisonGrid'
import { ExplanationPanel } from './ExplanationPanel'
import { HeadlineBanner } from './HeadlineBanner'
import { Legend } from './Legend'
import { MetricsChart } from './MetricsChart'
import { MetricsTable } from './MetricsTable'
import { Panel } from './Panel'

interface CompareTabProps {
  scenario: Scenario
  results: Results
  algorithms: AlgorithmName[]
  left: AlgorithmName
  right: AlgorithmName
  onLeftChange: (name: AlgorithmName) => void
  onRightChange: (name: AlgorithmName) => void
  selectedTicketId: string | null
  onSelectTicket: (ticketId: string | null) => void
  onTicketClick: (ticketId: string) => void
  onMapClick: (lat: number, lng: number) => void
  editMode: EditMode
  onEditModeChange: (mode: EditMode) => void
  edited: boolean
  onResetEdits: () => void
  sync: MapSync
  loading: boolean
  error: unknown
}

export function CompareTab(props: CompareTabProps) {
  const { scenario, results, left, right, editMode } = props
  const leftResult = results[left]
  const rightResult = results[right]
  const shown = [leftResult, rightResult].filter(
    (r, i, all): r is NonNullable<typeof r> => r !== undefined && all.findIndex((x) => x?.algorithm === r.algorithm) === i,
  )
  const toggle = (mode: EditMode) => props.onEditModeChange(editMode === mode ? 'none' : mode)

  return (
    <div className="compare">
      <HeadlineBanner left={leftResult} right={rightResult} loading={props.loading} />

      <div className="edit-toolbar" role="toolbar" aria-label="Edit scenario">
        <span className="muted small">
          {scenario.engineers.length} engineers · {scenario.tickets.length} tickets
          {props.edited && <span className="badge">edited</span>}
        </span>
        <button
          type="button"
          className={editMode === 'add-engineer' ? 'toggle active' : 'toggle'}
          aria-pressed={editMode === 'add-engineer'}
          onClick={() => toggle('add-engineer')}
        >
          Add engineer
        </button>
        <button
          type="button"
          className={editMode === 'delete-ticket' ? 'toggle active' : 'toggle'}
          aria-pressed={editMode === 'delete-ticket'}
          onClick={() => toggle('delete-ticket')}
        >
          Delete ticket
        </button>
        {props.edited && (
          <button type="button" className="ghost" onClick={props.onResetEdits}>
            Reset edits
          </button>
        )}
        {editMode !== 'none' && (
          <span className="hint" role="status">
            {editMode === 'add-engineer' ? 'Click a map to place an engineer' : 'Click a ticket to delete it'}
          </span>
        )}
      </div>

      <ComparisonGrid
        scenario={scenario}
        algorithms={props.algorithms}
        left={left}
        right={right}
        onLeftChange={props.onLeftChange}
        onRightChange={props.onRightChange}
        leftResult={leftResult}
        rightResult={rightResult}
        selectedTicketId={props.selectedTicketId}
        onTicketClick={props.onTicketClick}
        onMapClick={editMode === 'add-engineer' ? props.onMapClick : undefined}
        sync={props.sync}
        loading={props.loading}
        error={props.error}
      />
      <Legend />

      <ExplanationPanel
        scenario={scenario}
        results={shown}
        selectedTicketId={props.selectedTicketId}
        onSelectTicket={props.onSelectTicket}
      />

      <div className="report-row">
        <Panel title="Report card" testId="report-card" loading={props.loading}>
          <MetricsTable results={results} algorithms={props.algorithms} />
        </Panel>
        <Panel title="At a glance">
          <MetricsChart results={results} algorithms={props.algorithms} />
        </Panel>
      </div>
    </div>
  )
}
