import { render, screen, within } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import { makeResult } from '../test/fixtures'
import { MetricsTable } from './MetricsTable'

describe('MetricsTable', () => {
  it('shows one column per algorithm and highlights the best value per row', () => {
    const results = {
      greedy: makeResult('greedy', { assigned: 9, total_km: 100, objective: 40, gap_vs_best_pct: 33.3 }),
      hungarian: makeResult('hungarian', { assigned: 11, total_km: 90, objective: 30, gap_vs_best_pct: 0 }),
    }
    render(<MetricsTable results={results} algorithms={['greedy', 'hungarian', 'regret']} />)

    const table = screen.getByTestId('metrics-table')
    const headers = within(table).getAllByRole('columnheader').map((h) => h.textContent)
    expect(headers).toEqual(['Metric', 'Greedy', 'Hungarian'])

    const served = within(table).getByRole('row', { name: /Tickets served/ })
    const cells = within(served).getAllByRole('cell')
    expect(cells.map((c) => c.textContent)).toEqual(['9', '11'])
    expect(cells[1].className).toBe('best')
    expect(cells[0].className).toBe('')

    const travel = within(table).getByRole('row', { name: /Total travel/ })
    expect(within(travel).getAllByRole('cell')[1].className).toBe('best')
  })

  it('highlights nothing when every algorithm ties', () => {
    const results = { greedy: makeResult('greedy'), hungarian: makeResult('hungarian') }
    render(<MetricsTable results={results} algorithms={['greedy', 'hungarian']} />)
    expect(screen.getByTestId('metrics-table').querySelectorAll('td.best')).toHaveLength(0)
  })
})
