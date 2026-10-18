const MINUS = '−'

export function pct(value: number | null | undefined, digits = 1): string {
  return value == null ? '—' : `${value.toFixed(digits)}%`
}

export function km(value: number | null | undefined, digits = 1): string {
  return value == null ? '—' : `${value.toFixed(digits)} km`
}

export function num(value: number | null | undefined, digits = 1): string {
  return value == null ? '—' : value.toFixed(digits)
}

export function ms(value: number): string {
  return `${value < 10 ? value.toFixed(2) : value.toFixed(0)} ms`
}

/** "+1.5", "−2.0", "0.0" with a typographic minus. */
export function signed(value: number, digits = 1): string {
  const rounded = Number(value.toFixed(digits))
  if (rounded === 0) return (0).toFixed(digits)
  return `${rounded > 0 ? '+' : MINUS}${Math.abs(rounded).toFixed(digits)}`
}

export function plural(count: number, word: string, pluralWord = `${word}s`): string {
  return `${count} ${Math.abs(count) === 1 ? word : pluralWord}`
}

/** "HH:MM" from an ISO timestamp, in the timestamp's own offset (the dispatch timezone). */
export function clock(iso: string): string {
  const match = /T(\d{2}:\d{2})/.exec(iso)
  return match ? match[1] : iso
}

export function capitalize(text: string): string {
  return text.charAt(0).toUpperCase() + text.slice(1)
}

export const ALGORITHM_LABEL: Record<string, string> = {
  greedy: 'Greedy',
  hungarian: 'Hungarian',
  regret: 'Regret',
}

export function algorithmLabel(name: string): string {
  return ALGORITHM_LABEL[name] ?? capitalize(name)
}
