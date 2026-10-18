import type {
  AllocateRequest,
  AllocateResponse,
  ErrorEnvelope,
  GenerateRequest,
  Meta,
  Scenario,
  SweepRequest,
  SweepResponse,
} from './models'

const BASE_URL = (import.meta.env.VITE_API_URL ?? '').replace(/\/$/, '')

/** Every non-2xx response from the API carries the same envelope; this is its client side. */
export class ApiError extends Error {
  readonly status: number
  readonly code: string
  readonly details: Record<string, unknown>

  constructor(status: number, code: string, message: string, details: Record<string, unknown> = {}) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
    this.details = details
  }
}

function isEnvelope(body: unknown): body is ErrorEnvelope {
  if (typeof body !== 'object' || body === null || !('error' in body)) return false
  const error = (body as { error: unknown }).error
  return typeof error === 'object' && error !== null && 'code' in error && 'message' in error
}

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  let response: Response
  try {
    response = await fetch(`${BASE_URL}${path}`, {
      ...init,
      headers: {
        Accept: 'application/json',
        ...(init?.body ? { 'Content-Type': 'application/json' } : {}),
      },
    })
  } catch {
    throw new ApiError(0, 'NETWORK_ERROR', 'Cannot reach the API. Is the backend running?')
  }

  const text = await response.text()
  let body: unknown = null
  if (text) {
    try {
      body = JSON.parse(text)
    } catch {
      body = null
    }
  }
  if (!response.ok) {
    if (isEnvelope(body)) {
      throw new ApiError(response.status, body.error.code, body.error.message, body.error.details ?? {})
    }
    throw new ApiError(response.status, 'HTTP_ERROR', `Request failed with status ${response.status}`)
  }
  return body as T
}

function post<T>(path: string, body: unknown): Promise<T> {
  return request<T>(path, { method: 'POST', body: JSON.stringify(body) })
}

export const api = {
  meta: () => request<Meta>('/api/meta'),
  generate: (body: GenerateRequest) => post<Scenario>('/api/scenarios/generate', body),
  allocate: (body: AllocateRequest) => post<AllocateResponse>('/api/allocate', body),
  sweep: (body: SweepRequest) => post<SweepResponse>('/api/experiments/sweep', body),
}
