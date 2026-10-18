import { afterEach, describe, expect, it, vi } from 'vitest'
import { api, ApiError } from './client'

function respond(status: number, body: unknown) {
  return vi.fn(async () => new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } }))
}

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('api client', () => {
  it('returns parsed JSON on success', async () => {
    vi.stubGlobal('fetch', respond(200, { status: 'ok' }))
    await expect(api.meta()).resolves.toEqual({ status: 'ok' })
  })

  it('turns the error envelope into an ApiError', async () => {
    const envelope = {
      error: { code: 'ESTIMATOR_UNAVAILABLE', message: "ML estimator is not loaded; use 'naive'.", details: {} },
    }
    vi.stubGlobal('fetch', respond(400, envelope))
    const error = await api.meta().catch((e: unknown) => e)
    expect(error).toBeInstanceOf(ApiError)
    expect(error).toMatchObject({ status: 400, code: 'ESTIMATOR_UNAVAILABLE', message: "ML estimator is not loaded; use 'naive'." })
  })

  it('reports a network failure in plain words', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn(async () => {
        throw new TypeError('Failed to fetch')
      }),
    )
    await expect(api.meta()).rejects.toMatchObject({ code: 'NETWORK_ERROR', status: 0 })
  })

  it('posts JSON bodies', async () => {
    const fetchMock = respond(200, { id: 'sc_1_1_1' })
    vi.stubGlobal('fetch', fetchMock)
    await api.generate({ seed: 1, num_engineers: 1, num_tickets: 1 })
    expect(fetchMock).toHaveBeenCalledWith(
      '/api/scenarios/generate',
      expect.objectContaining({ method: 'POST', body: '{"seed":1,"num_engineers":1,"num_tickets":1}' }),
    )
  })
})
