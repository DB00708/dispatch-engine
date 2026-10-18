import type { Engineer, FaultType, Scenario } from '../api/models'

export const ALL_FAULT_TYPES: FaultType[] = ['electrical', 'mechanical', 'hydraulic', 'controls']

/** "2026-10-20T09:00:00+05:30" -> "2026-10-20T08:00:00+05:30" for hour 8. */
export function atHour(dispatchTime: string, hour: number): string {
  const date = dispatchTime.slice(0, 10)
  const offset = dispatchTime.slice(19) || 'Z'
  return `${date}T${String(hour).padStart(2, '0')}:00:00${offset}`
}

/** Next free id with the given prefix: E01, E02 ... (keeps the 2-digit style, grows past 99). */
export function nextId(prefix: string, existing: string[]): string {
  const numbers = existing
    .filter((id) => id.startsWith(prefix))
    .map((id) => Number.parseInt(id.slice(prefix.length), 10))
    .filter((n) => Number.isFinite(n))
  const next = (numbers.length ? Math.max(...numbers) : 0) + 1
  return `${prefix}${String(next).padStart(2, '0')}`
}

/** A fully-skilled day-shift engineer dropped on the map at (lat, lng). */
export function addEngineer(scenario: Scenario, lat: number, lng: number): Scenario {
  const id = nextId('E', scenario.engineers.map((e) => e.id))
  const engineer: Engineer = {
    id,
    name: `Added ${id}`,
    location: { lat: Number(lat.toFixed(5)), lng: Number(lng.toFixed(5)) },
    skills: [...ALL_FAULT_TYPES],
    shift_start: atHour(scenario.dispatch_time, 8),
    shift_end: atHour(scenario.dispatch_time, 17),
    experience_years: 5,
  }
  return { ...scenario, engineers: [...scenario.engineers, engineer] }
}

export function deleteTicket(scenario: Scenario, ticketId: string): Scenario {
  return { ...scenario, tickets: scenario.tickets.filter((t) => t.id !== ticketId) }
}
