import { useState } from 'react'
import type { AlgorithmName, AllocationConfig, Meta } from '../api/models'
import { useSweep } from '../hooks/useSweep'
import { ALGORITHMS } from '../lib/controls'
import { algorithmLabel, ms, pct } from '../lib/format'
import { parseRatios, summarize } from '../lib/sweep'
import { Panel } from './Panel'
import { SweepChart } from './SweepChart'

interface ExperimentTabProps {
  config: AllocationConfig
  meta: Meta | undefined
}

/** The scarcity sweep: the evidence behind the algorithm comparison write-up. */
export default function ExperimentTab({ config, meta }: ExperimentTabProps) {
  const sweep = useSweep()
  const [numTickets, setNumTickets] = useState(30)
  const [ratiosText, setRatiosText] = useState('0.3, 0.5, 0.75, 1, 1.25, 1.5')
  const [seeds, setSeeds] = useState(20)
  const [algorithms, setAlgorithms] = useState<AlgorithmName[]>(ALGORITHMS)

  const limits = meta?.limits
  const ratios = parseRatios(ratiosText)
  const ratioError =
    ratios === null
      ? 'Enter positive numbers separated by commas.'
      : limits && ratios.length > limits.sweep_max_ratios
        ? `At most ${limits.sweep_max_ratios} ratios.`
        : null
  const canRun = ratios !== null && ratioError === null && algorithms.length > 0 && !sweep.isPending

  const points = sweep.data?.points ?? []
  const ran = sweep.data ? ALGORITHMS.filter((a) => points.some((p) => p.algorithm === a)) : []

  return (
    <div className="experiment">
      <Panel title="Scarcity sweep" testId="sweep-form">
        <p className="muted">
          Fix the tickets, vary how many engineers there are per ticket, and average each algorithm over many seeded
          scenarios. Uses the weights and limits from the Compare tab.
        </p>
        <form
          className="sweep-form"
          onSubmit={(event) => {
            event.preventDefault()
            if (!canRun || ratios === null) return
            sweep.mutate({ num_tickets: numTickets, ratios, seeds_per_ratio: seeds, algorithms, config })
          }}
        >
          <div className="field">
            <label htmlFor="sweep-tickets">Tickets</label>
            <input
              id="sweep-tickets"
              type="number"
              min={1}
              max={limits?.sweep_max_tickets ?? 100}
              value={numTickets}
              onChange={(event) => setNumTickets(Math.max(1, Number(event.target.value) || 1))}
            />
          </div>
          <div className="field grow">
            <label htmlFor="sweep-ratios">Engineers per ticket</label>
            <input
              id="sweep-ratios"
              value={ratiosText}
              onChange={(event) => setRatiosText(event.target.value)}
              aria-invalid={ratioError !== null}
            />
          </div>
          <div className="field">
            <label htmlFor="sweep-seeds">Seeds per ratio</label>
            <input
              id="sweep-seeds"
              type="number"
              min={1}
              max={limits?.sweep_max_seeds ?? 50}
              value={seeds}
              onChange={(event) => setSeeds(Math.max(1, Number(event.target.value) || 1))}
            />
          </div>
          <fieldset className="field checks">
            <legend>Algorithms</legend>
            {ALGORITHMS.map((name) => (
              <label key={name}>
                <input
                  type="checkbox"
                  checked={algorithms.includes(name)}
                  onChange={(event) =>
                    setAlgorithms((current) =>
                      event.target.checked
                        ? ALGORITHMS.filter((a) => a === name || current.includes(a))
                        : current.filter((a) => a !== name),
                    )
                  }
                />
                {algorithmLabel(name)}
              </label>
            ))}
          </fieldset>
          <button type="submit" className="primary" disabled={!canRun}>
            {sweep.isPending ? 'Running…' : 'Run sweep'}
          </button>
        </form>
        {ratioError && <p className="field-error">{ratioError}</p>}
      </Panel>

      <Panel title="Results" testId="sweep-results" loading={sweep.isPending} error={sweep.error}>
        {sweep.data ? (
          <>
            <ul className="findings" data-testid="sweep-findings">
              {summarize(points).map((line) => (
                <li key={line}>{line}</li>
              ))}
            </ul>
            <div className="sweep-charts">
              <SweepChart
                title="Mean objective gap vs best (%)"
                points={points}
                metric="mean_gap_pct"
                algorithms={ran}
                unit="%"
                testId="sweep-gap-chart"
              />
              <SweepChart
                title="Gap in the worst 10% of scenarios (%)"
                points={points}
                metric="p90_gap_pct"
                algorithms={ran}
                unit="%"
                testId="sweep-p90-chart"
              />
              <SweepChart
                title="P1 coverage (%)"
                points={points}
                metric="mean_p1_coverage_pct"
                algorithms={ran}
                unit="%"
                testId="sweep-p1-chart"
              />
              <SweepChart
                title="Runtime (ms)"
                points={points}
                metric="mean_runtime_ms"
                algorithms={ran}
                unit=" ms"
                testId="sweep-runtime-chart"
              />
            </div>
            <div className="table-wrap">
              <table className="sweep-table" data-testid="sweep-table">
                <thead>
                  <tr>
                    <th>Ratio</th>
                    <th>Engineers</th>
                    <th>Algorithm</th>
                    <th>Mean gap</th>
                    <th>p90 gap</th>
                    <th>Coverage</th>
                    <th>P1 coverage</th>
                    <th>Runtime</th>
                  </tr>
                </thead>
                <tbody>
                  {points.map((p) => (
                    <tr key={`${p.ratio}-${p.algorithm}`}>
                      <td>{p.ratio}</td>
                      <td>{p.num_engineers}</td>
                      <td>{algorithmLabel(p.algorithm)}</td>
                      <td>{pct(p.mean_gap_pct)}</td>
                      <td>{pct(p.p90_gap_pct)}</td>
                      <td>{pct(p.mean_coverage_pct)}</td>
                      <td>{pct(p.mean_p1_coverage_pct)}</td>
                      <td>{ms(p.mean_runtime_ms)}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          </>
        ) : (
          !sweep.isPending && <p className="muted">Press Run sweep to compare the algorithms across scarcity levels.</p>
        )}
      </Panel>
    </div>
  )
}
