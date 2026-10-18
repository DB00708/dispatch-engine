import type { AllocationResult, Scenario, Ticket } from '../api/models'
import { algorithmLabel, clock, km } from '../lib/format'
import { Panel } from './Panel'

function Decision({ result, ticket }: { result: AllocationResult; ticket: Ticket }) {
  const assignment = result.assignments.find((a) => a.ticket_id === ticket.id)
  const unassigned = result.unassigned.find((u) => u.ticket_id === ticket.id)
  return (
    <div className="decision" data-testid={`decision-${result.algorithm}`}>
      <h3>{algorithmLabel(result.algorithm)}</h3>
      {assignment ? (
        <>
          <p className="decision-main">
            <strong>
              → {assignment.engineer_id}
            </strong>{' '}
            · {km(assignment.road_km)} · ETA {clock(assignment.start)} · finish {clock(assignment.finish)} ·{' '}
            {assignment.slack_min} min spare
          </p>
          <p>{assignment.explanation.summary}.</p>
          <p className="muted small">
            Cost {assignment.cost.toFixed(2)} = distance {assignment.cost_breakdown.distance.toFixed(2)} + margin{' '}
            {assignment.cost_breakdown.slack.toFixed(2)}
          </p>
          {assignment.explanation.runner_ups.length > 0 && (
            <ul className="runner-ups">
              {assignment.explanation.runner_ups.map((r) => (
                <li key={r.engineer_id} className={r.feasible ? 'feasible' : 'blocked'}>
                  <strong>{r.engineer_id}</strong> {r.feasible ? 'could go: ' : 'not allowed: '}
                  {r.note}
                </li>
              ))}
            </ul>
          )}
        </>
      ) : unassigned ? (
        <>
          <p className="decision-main">
            <strong>Left unassigned</strong> · penalty {unassigned.penalty}
          </p>
          <ul className="reasons">
            {unassigned.reasons.map((reason) => (
              <li key={reason}>{reason}</li>
            ))}
          </ul>
        </>
      ) : (
        <p className="muted">Not part of this result yet.</p>
      )}
    </div>
  )
}

interface ExplanationPanelProps {
  scenario: Scenario
  results: AllocationResult[]
  selectedTicketId: string | null
  onSelectTicket: (ticketId: string | null) => void
}

/** Why each decision was made: click a ticket or a line on either map. */
export function ExplanationPanel({ scenario, results, selectedTicketId, onSelectTicket }: ExplanationPanelProps) {
  const ticket = scenario.tickets.find((t) => t.id === selectedTicketId)
  const unservedSomewhere = scenario.tickets.filter((t) =>
    results.some((r) => r.unassigned.some((u) => u.ticket_id === t.id)),
  )
  return (
    <Panel
      testId="explanation"
      title={ticket ? `Why? ${ticket.id}` : 'Why? Click any ticket or line'}
      actions={
        ticket && (
          <button type="button" className="ghost" onClick={() => onSelectTicket(null)}>
            Clear
          </button>
        )
      }
    >
      {ticket ? (
        <>
          <p className="ticket-meta">
            <span className={`pill ${ticket.priority.toLowerCase()}`}>{ticket.priority}</span> {ticket.fault_type} ·
            due {clock(ticket.deadline)} · equipment {ticket.equipment_age_years} yrs old
          </p>
          <div className="decisions">
            {results.map((result) => (
              <Decision key={result.algorithm} result={result} ticket={ticket} />
            ))}
          </div>
        </>
      ) : unservedSomewhere.length > 0 ? (
        <ul className="unserved-list">
          {unservedSomewhere.map((t) => {
            const by = results.filter((r) => r.unassigned.some((u) => u.ticket_id === t.id))
            const reason = by[0]?.unassigned.find((u) => u.ticket_id === t.id)?.reasons[0]
            return (
              <li key={t.id}>
                <button type="button" className="link" onClick={() => onSelectTicket(t.id)}>
                  {t.id}
                </button>{' '}
                <span className={`pill ${t.priority.toLowerCase()}`}>{t.priority}</span> left unassigned by{' '}
                {by.map((r) => algorithmLabel(r.algorithm)).join(' and ')}: {reason}
              </li>
            )
          })}
        </ul>
      ) : (
        <p className="muted">Every ticket is served by both algorithms. Click a ticket to see why it got its engineer.</p>
      )}
    </Panel>
  )
}
