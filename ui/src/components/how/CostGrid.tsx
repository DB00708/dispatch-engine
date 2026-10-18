import type { Trace } from '../../api/models'
import { cellKey } from '../../lib/trace'

export interface CellMark {
  kind: 'pick' | 'chosen' | 'grabbed' | 'current'
  label?: string
}

interface CostGridProps {
  trace: Trace
  marks?: Map<string, CellMark>
  maxRows?: number
  maxCols?: number
  compact?: boolean
  testId: string
  caption?: string
  onHover?: (cell: { i: number; j: number } | null) => void
}

/** Tickets x engineers. Darker = cheaper pairing, crossed = not allowed. */
export function CostGrid({ trace, marks, maxRows = 30, maxCols = 30, compact, testId, caption, onHover }: CostGridProps) {
  const rows = trace.ticket_ids.slice(0, maxRows)
  const cols = trace.engineer_ids.slice(0, maxCols)
  const allowed = trace.cost_grid
    .slice(0, maxRows)
    .flatMap((row) => row.slice(0, maxCols))
    .filter((c): c is number => c !== null)
  const low = allowed.length ? Math.min(...allowed) : 0
  const high = allowed.length ? Math.max(...allowed) : 1
  const shade = (cost: number) => 0.14 + 0.76 * (1 - (high > low ? (cost - low) / (high - low) : 0))
  const truncated = trace.ticket_ids.length > rows.length || trace.engineer_ids.length > cols.length

  return (
    <div className={`cost-grid-wrap${compact ? ' compact' : ''}`}>
      {caption && <p className="grid-caption">{caption}</p>}
      <div className="table-wrap">
        <table className="cost-grid" data-testid={testId} onMouseLeave={() => onHover?.(null)}>
          <thead>
            <tr>
              <th scope="col" aria-label="Ticket" />
              {cols.map((id) => (
                <th scope="col" key={id}>
                  {id}
                </th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((ticketId, i) => (
              <tr key={ticketId}>
                <th scope="row">{ticketId}</th>
                {cols.map((engineerId, j) => {
                  const cost = trace.cost_grid[i][j]
                  const mark = marks?.get(cellKey(ticketId, engineerId))
                  const classes = ['cell', cost === null ? 'blocked' : 'allowed', mark?.kind].filter(Boolean)
                  return (
                    <td
                      key={engineerId}
                      className={classes.join(' ')}
                      style={cost === null ? undefined : { background: `rgba(79, 107, 237, ${shade(cost).toFixed(2)})` }}
                      title={
                        cost === null
                          ? `${ticketId} × ${engineerId}: not allowed (${trace.violations_grid[i][j].join(', ')})`
                          : `${ticketId} × ${engineerId}: cost ${cost.toFixed(2)}, ${trace.road_km_grid[i][j]} km, ${trace.slack_min_grid[i][j]} min spare`
                      }
                      onMouseEnter={() => onHover?.({ i, j })}
                    >
                      {mark?.label ?? ''}
                    </td>
                  )
                })}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      {truncated && (
        <p className="muted small">
          Showing the first {rows.length} of {trace.ticket_ids.length} tickets and {cols.length} of{' '}
          {trace.engineer_ids.length} engineers.
        </p>
      )}
    </div>
  )
}
