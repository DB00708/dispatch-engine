import type { Meta } from '../api/models'
import type { Controls } from '../lib/controls'

interface RangeFieldProps {
  label: string
  value: number
  min: number
  max: number
  step?: number
  inputMax?: number
  onChange: (value: number) => void
  suffix?: string
}

function RangeField({ label, value, min, max, step = 1, inputMax, onChange, suffix }: RangeFieldProps) {
  const id = `ctl-${label.toLowerCase().replace(/\s+/g, '-')}`
  const commit = (raw: string) => {
    const parsed = Number(raw)
    if (raw === '' || !Number.isFinite(parsed)) return
    onChange(Math.min(Math.max(parsed, min), inputMax ?? max))
  }
  return (
    <div className="field range-field">
      <label htmlFor={id}>{label}</label>
      <div className="range-row">
        <input
          type="range"
          min={min}
          max={max}
          step={step}
          value={Math.min(value, max)}
          onChange={(event) => commit(event.target.value)}
          aria-label={`${label} slider`}
        />
        <input
          id={id}
          type="number"
          min={min}
          max={inputMax ?? max}
          step={step}
          value={value}
          onChange={(event) => commit(event.target.value)}
        />
        {suffix && <span className="suffix">{suffix}</span>}
      </div>
    </div>
  )
}

interface ControlsPanelProps {
  controls: Controls
  meta: Meta | undefined
  onChange: (patch: Partial<Controls>) => void
  onRun: () => void
  running: boolean
}

export function ControlsPanel({ controls, meta, onChange, onRun, running }: ControlsPanelProps) {
  const maxEngineers = meta?.limits.max_engineers ?? 200
  const maxTickets = meta?.limits.max_tickets ?? 200
  const estimators = meta?.estimators ?? ['naive']
  return (
    <form
      className="controls"
      aria-label="Scenario and allocation controls"
      onSubmit={(event) => {
        event.preventDefault()
        onRun()
      }}
    >
      <div className="field seed-field">
        <label htmlFor="ctl-seed">Seed</label>
        <div className="range-row">
          <input
            id="ctl-seed"
            type="number"
            min={0}
            value={controls.seed}
            onChange={(event) => {
              const seed = Number(event.target.value)
              if (event.target.value !== '' && Number.isInteger(seed) && seed >= 0) onChange({ seed })
            }}
          />
          <button
            type="button"
            className="icon-button"
            aria-label="Random seed"
            title="Random seed"
            onClick={() => onChange({ seed: Math.floor(Math.random() * 100_000) })}
          >
            ↻
          </button>
        </div>
      </div>
      <RangeField
        label="Engineers"
        value={controls.numEngineers}
        min={0}
        max={Math.min(60, maxEngineers)}
        inputMax={maxEngineers}
        onChange={(numEngineers) => onChange({ numEngineers })}
      />
      <RangeField
        label="Tickets"
        value={controls.numTickets}
        min={1}
        max={Math.min(60, maxTickets)}
        inputMax={maxTickets}
        onChange={(numTickets) => onChange({ numTickets })}
      />
      <RangeField
        label="Distance weight"
        value={controls.weights.distance}
        min={0}
        max={3}
        step={0.1}
        onChange={(distance) => onChange({ weights: { ...controls.weights, distance } })}
      />
      <RangeField
        label="Margin weight"
        value={controls.weights.slack}
        min={0}
        max={3}
        step={0.1}
        onChange={(slack) => onChange({ weights: { ...controls.weights, slack } })}
      />
      <RangeField
        label="Max distance"
        value={controls.maxDistanceKm}
        min={5}
        max={60}
        inputMax={200}
        onChange={(maxDistanceKm) => onChange({ maxDistanceKm })}
        suffix="km"
      />
      <RangeField
        label="Speed"
        value={controls.speedKmph}
        min={10}
        max={60}
        inputMax={150}
        onChange={(speedKmph) => onChange({ speedKmph })}
        suffix="km/h"
      />
      {estimators.length > 1 && (
        <div className="field">
          <label htmlFor="ctl-estimator">Estimator</label>
          <select
            id="ctl-estimator"
            value={controls.estimator}
            onChange={(event) => onChange({ estimator: event.target.value as Controls['estimator'] })}
          >
            {estimators.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      )}
      <button type="submit" className="primary run-button" disabled={running}>
        {running ? 'Running…' : 'Run'}
      </button>
    </form>
  )
}
