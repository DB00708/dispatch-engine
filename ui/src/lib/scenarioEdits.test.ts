import { describe, expect, it } from 'vitest'
import { SCENARIO } from '../test/fixtures'
import { addEngineer, atHour, deleteTicket, nextId } from './scenarioEdits'

describe('scenario edits', () => {
  it('builds shift times in the dispatch timezone', () => {
    expect(atHour('2026-10-20T09:00:00+05:30', 8)).toBe('2026-10-20T08:00:00+05:30')
    expect(atHour('2026-10-20T09:00:00Z', 17)).toBe('2026-10-20T17:00:00Z')
  })

  it('picks the next free id', () => {
    expect(nextId('E', ['E01', 'E07', 'E03'])).toBe('E08')
    expect(nextId('E', [])).toBe('E01')
    expect(nextId('E', ['E99'])).toBe('E100')
  })

  it('adds a fully skilled engineer without touching the original', () => {
    const edited = addEngineer(SCENARIO, 12.951234567, 77.6098765)
    expect(SCENARIO.engineers).toHaveLength(2)
    expect(edited.engineers).toHaveLength(3)
    const added = edited.engineers[2]
    expect(added.id).toBe('E03')
    expect(added.location).toEqual({ lat: 12.95123, lng: 77.60988 })
    expect(added.skills).toEqual(['electrical', 'mechanical', 'hydraulic', 'controls'])
    expect(added.shift_start).toBe('2026-10-20T08:00:00+05:30')
  })

  it('deletes a ticket by id', () => {
    const edited = deleteTicket(SCENARIO, 'T01')
    expect(edited.tickets.map((t) => t.id)).toEqual(['T02'])
    expect(SCENARIO.tickets).toHaveLength(2)
  })
})
