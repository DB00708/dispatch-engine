import { useMemo } from 'react'
import type { AlgorithmName, AllocationResult, Scenario } from '../api/models'
import { algorithmLabel, ms } from '../lib/format'
import { resultLayers } from '../lib/mapLayers'
import type { MapSync } from '../lib/mapSync'
import { MapView } from './MapView'
import { MetricChips } from './MetricChips'
import { Panel } from './Panel'

interface AlgorithmPanelProps {
  side: 'left' | 'right'
  algorithm: AlgorithmName
  algorithms: AlgorithmName[]
  onAlgorithmChange: (name: AlgorithmName) => void
  scenario: Scenario
  result: AllocationResult | undefined
  other: AllocationResult | undefined
  selectedTicketId: string | null
  onTicketClick: (ticketId: string) => void
  onMapClick?: (lat: number, lng: number) => void
  sync: MapSync
  loading: boolean
  error: unknown
}

function AlgorithmPanel(props: AlgorithmPanelProps) {
  const { side, algorithm, algorithms, onAlgorithmChange, scenario, result, other, sync } = props
  const layers = useMemo(() => resultLayers(scenario, result), [scenario, result])
  return (
    <Panel
      testId={`panel-${side}`}
      className="algo-panel"
      loading={props.loading}
      error={props.error}
      title={
        <select
          className="algo-select"
          aria-label={`${side === 'left' ? 'Left' : 'Right'} algorithm`}
          value={algorithm}
          onChange={(event) => onAlgorithmChange(event.target.value as AlgorithmName)}
        >
          {algorithms.map((name) => (
            <option key={name} value={name}>
              {algorithmLabel(name)}
            </option>
          ))}
        </select>
      }
      actions={
        result && (
          <span className="runtime" data-testid={`runtime-${side}`}>
            {ms(result.runtime_ms)}
          </span>
        )
      }
    >
      <MapView
        name={side}
        scenario={scenario}
        layers={layers}
        selectedTicketId={props.selectedTicketId}
        onTicketClick={props.onTicketClick}
        onMapClick={props.onMapClick}
        crosshair={props.onMapClick !== undefined}
        sync={sync}
      />
      {result && <MetricChips result={result} other={other} />}
    </Panel>
  )
}

interface ComparisonGridProps extends Omit<AlgorithmPanelProps, 'side' | 'algorithm' | 'onAlgorithmChange' | 'result' | 'other'> {
  left: AlgorithmName
  right: AlgorithmName
  onLeftChange: (name: AlgorithmName) => void
  onRightChange: (name: AlgorithmName) => void
  leftResult: AllocationResult | undefined
  rightResult: AllocationResult | undefined
}

/** Two maps side by side, panned and zoomed together. */
export function ComparisonGrid({
  left,
  right,
  onLeftChange,
  onRightChange,
  leftResult,
  rightResult,
  ...shared
}: ComparisonGridProps) {
  return (
    <div className="compare-grid">
      <AlgorithmPanel
        {...shared}
        side="left"
        algorithm={left}
        onAlgorithmChange={onLeftChange}
        result={leftResult}
        other={rightResult}
      />
      <AlgorithmPanel
        {...shared}
        side="right"
        algorithm={right}
        onAlgorithmChange={onRightChange}
        result={rightResult}
        other={leftResult}
      />
    </div>
  )
}
