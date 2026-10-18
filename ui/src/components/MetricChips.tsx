import type { AllocationResult } from '../api/models'
import { km, num, pct, signed } from '../lib/format'

type Direction = 'higher' | 'lower'

interface ChipProps {
  id: string
  label: string
  value: string
  delta?: number | null
  digits?: number
  unit?: string
  better?: Direction
  note?: string
}

function Chip({ id, label, value, delta, digits = 1, unit = '', better, note }: ChipProps) {
  let tone = ''
  if (delta != null && better && Math.abs(delta) >= 10 ** -digits / 2) {
    const good = better === 'higher' ? delta > 0 : delta < 0
    tone = good ? 'good' : 'bad'
  }
  return (
    <div className="chip" data-testid={`chip-${id}`}>
      <span className="chip-label">{label}</span>
      <span className="chip-value">{value}</span>
      <span className={`chip-sub ${tone}`}>
        {delta != null ? `${signed(delta, digits)}${unit} vs other` : (note ?? ' ')}
      </span>
    </div>
  )
}

function diff(a: number | null | undefined, b: number | null | undefined): number | null {
  return a == null || b == null ? null : a - b
}

interface MetricChipsProps {
  result: AllocationResult
  other?: AllocationResult
}

/** Six chips under each map: every solved constraint and metric, with the difference to the other panel. */
export function MetricChips({ result, other }: MetricChipsProps) {
  const m = result.metrics
  const o = other && other.algorithm !== result.algorithm ? other.metrics : undefined
  const unserved = m.unserved_by_priority
  const gap = m.gap_vs_best_pct
  return (
    <div className="chips">
      <Chip
        id="coverage"
        label="Coverage"
        value={pct(m.coverage_pct)}
        delta={o ? diff(m.coverage_pct, o.coverage_pct) : null}
        unit=" pts"
        better="higher"
        note={`${m.assigned} of ${m.total_tickets} tickets`}
      />
      <Chip
        id="p1"
        label="P1 served"
        value={pct(m.p1_coverage_pct)}
        delta={o ? diff(m.p1_coverage_pct, o.p1_coverage_pct) : null}
        unit=" pts"
        better="higher"
        note={m.p1_coverage_pct == null ? 'no P1 tickets' : undefined}
      />
      <Chip
        id="km"
        label="Total km"
        value={km(m.total_km)}
        delta={o ? diff(m.total_km, o.total_km) : null}
        unit=" km"
        better="lower"
      />
      <Chip
        id="tight"
        label="Tight SLAs"
        value={String(m.tight_assignments)}
        delta={o ? diff(m.tight_assignments, o.tight_assignments) : null}
        digits={0}
        better="lower"
      />
      <Chip
        id="unserved"
        label="Unserved"
        value={`P1 ${unserved.P1} · P2 ${unserved.P2} · P3 ${unserved.P3}`}
        note="by priority"
      />
      <Chip
        id="objective"
        label="Objective"
        value={num(m.objective, 1)}
        note={gap == null ? ' ' : gap < 0.05 ? 'best of all three' : `+${gap.toFixed(1)}% vs best`}
      />
    </div>
  )
}
