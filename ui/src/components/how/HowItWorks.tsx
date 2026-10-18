import { useEffect, useReducer, useState } from 'react'
import type { AlgorithmName, AllocationConfig, Scenario } from '../../api/models'
import { useAllocate } from '../../hooks/useAllocate'
import { algorithmLabel } from '../../lib/format'
import { defaultFocusTicket, isSequential } from '../../lib/trace'
import { Panel } from '../Panel'
import { StepAssign, StepCost, StepFilter, StepReport, StepScenario } from './steps'

const STEPS = ['Scenario', 'Hard filter', 'Cost grid', 'Assign', 'Report card'] as const

interface PlayState {
  step: number
  pick: number
  playing: boolean
}

type Action =
  | { type: 'go'; step: number }
  | { type: 'pick'; pick: number }
  | { type: 'toggle' }
  | { type: 'tick'; picks: number }

function reducer(state: PlayState, action: Action): PlayState {
  switch (action.type) {
    case 'go':
      return { step: action.step, pick: action.step === 4 ? 0 : state.pick, playing: false }
    case 'pick':
      return { ...state, pick: action.pick, playing: false }
    case 'toggle':
      if (state.playing) return { ...state, playing: false }
      return state.step === STEPS.length ? { step: 1, pick: 0, playing: true } : { ...state, playing: true }
    case 'tick':
      if (!state.playing) return state
      if (state.step === 4 && state.pick < action.picks) return { ...state, pick: state.pick + 1 }
      if (state.step < STEPS.length) return { ...state, step: state.step + 1, pick: 0 }
      return { ...state, playing: false }
  }
}

interface HowItWorksProps {
  scenario: Scenario
  config: AllocationConfig
  left: AlgorithmName
  right: AlgorithmName
  onOpenExperiment: () => void
}

/** L1: replays one run as five steps on the real scenario. */
export default function HowItWorks({ scenario, config, left, right, onOpenExperiment }: HowItWorksProps) {
  const algorithms = left === right ? [left] : [left, right]
  const query = useAllocate({ scenario, config, algorithms, includeTrace: true })
  const leftResult = query.data?.results[left]
  const rightResult = query.data?.results[right]
  const trace = leftResult?.trace ?? rightResult?.trace ?? undefined

  const [state, dispatch] = useReducer(reducer, { step: 1, pick: 0, playing: false })
  const [chosenTicket, setChosenTicket] = useState<string | null>(null)

  // Show the sequential algorithm's picks on the left of step 4 when only one is sequential.
  const [seqResult, setResult] =
    leftResult && rightResult && !isSequential(leftResult) && isSequential(rightResult)
      ? [rightResult, leftResult]
      : [leftResult, rightResult]
  const picks = seqResult?.trace?.pick_order.length ?? 0
  const pick = Math.min(state.pick, picks)

  useEffect(() => {
    if (!state.playing) return
    const timer = window.setInterval(() => dispatch({ type: 'tick', picks }), state.step === 4 ? 700 : 2600)
    return () => window.clearInterval(timer)
  }, [state.playing, state.step, picks])

  const focusTicketId =
    chosenTicket && scenario.tickets.some((t) => t.id === chosenTicket)
      ? chosenTicket
      : trace
        ? defaultFocusTicket(trace, scenario)
        : undefined

  return (
    <Panel
      testId="how-it-works"
      title={`How it works: ${algorithmLabel(left)} vs ${algorithmLabel(right)}`}
      loading={query.isFetching}
      error={query.error}
    >
      <div className="stepper" role="tablist" aria-label="Steps">
        {STEPS.map((label, index) => {
          const step = index + 1
          return (
            <button
              key={label}
              type="button"
              role="tab"
              aria-selected={state.step === step}
              className={`step-pill${state.step === step ? ' active' : ''}${state.step > step ? ' done' : ''}`}
              onClick={() => dispatch({ type: 'go', step })}
            >
              {step} {label}
            </button>
          )
        })}
        <button type="button" className="play" onClick={() => dispatch({ type: 'toggle' })} data-testid="play">
          {state.playing ? 'Pause' : 'Play'}
        </button>
      </div>

      <div className="step" data-testid={`step-${state.step}`}>
        {state.step === 1 && <StepScenario scenario={scenario} />}
        {state.step > 1 && !trace && <p className="muted">Loading the cost grid…</p>}
        {state.step === 2 && trace && focusTicketId && (
          <StepFilter
            scenario={scenario}
            trace={trace}
            config={config}
            focusTicketId={focusTicketId}
            onFocus={setChosenTicket}
          />
        )}
        {state.step === 3 && trace && <StepCost trace={trace} config={config} />}
        {state.step === 4 && seqResult && setResult && (
          <StepAssign
            scenario={scenario}
            left={seqResult}
            right={setResult}
            pick={pick}
            onPick={(value) => dispatch({ type: 'pick', pick: value })}
          />
        )}
        {state.step === 5 && leftResult && rightResult && (
          <StepReport left={leftResult} right={rightResult} onOpenExperiment={onOpenExperiment} />
        )}
      </div>
    </Panel>
  )
}
