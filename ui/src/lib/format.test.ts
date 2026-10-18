import { describe, expect, it } from 'vitest'
import { algorithmLabel, clock, km, ms, pct, plural, signed } from './format'

describe('format helpers', () => {
  it('formats nullable numbers with a dash', () => {
    expect(pct(91.66)).toBe('91.7%')
    expect(pct(null)).toBe('—')
    expect(km(7.84)).toBe('7.8 km')
    expect(km(undefined)).toBe('—')
  })

  it('signs deltas with a real minus and never shows -0', () => {
    expect(signed(4.2)).toBe('+4.2')
    expect(signed(-1.25, 1)).toBe('−1.3')
    expect(signed(-0.01)).toBe('0.0')
  })

  it('reads the clock time in the timestamp offset, not the browser timezone', () => {
    expect(clock('2026-10-20T09:16:00+05:30')).toBe('09:16')
    expect(clock('2026-10-20T23:05:00Z')).toBe('23:05')
  })

  it('pluralises and labels', () => {
    expect(plural(1, 'ticket')).toBe('1 ticket')
    expect(plural(3, 'ticket')).toBe('3 tickets')
    expect(ms(0.456)).toBe('0.46 ms')
    expect(ms(42.4)).toBe('42 ms')
    expect(algorithmLabel('hungarian')).toBe('Hungarian')
  })
})
