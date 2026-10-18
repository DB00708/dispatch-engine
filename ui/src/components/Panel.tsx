import type { ReactNode } from 'react'
import { ApiError } from '../api/client'

export function Spinner({ label = 'Loading' }: { label?: string }) {
  return <span className="spinner" role="status" aria-label={label} />
}

export function ErrorNote({ error }: { error: unknown }) {
  const message =
    error instanceof Error ? error.message : typeof error === 'string' ? error : 'Something went wrong.'
  const code = error instanceof ApiError ? error.code : null
  return (
    <div className="error-note" role="alert" data-testid="error-note">
      {code && <code>{code}</code>} {message}
    </div>
  )
}

interface PanelProps {
  title?: ReactNode
  actions?: ReactNode
  loading?: boolean
  error?: unknown
  className?: string
  testId?: string
  children?: ReactNode
}

/** A card. Its own spinner and error line, so one failing call never blanks the page. */
export function Panel({ title, actions, loading, error, className = '', testId, children }: PanelProps) {
  const hasHead = title !== undefined || actions !== undefined || loading
  return (
    <section className={`panel ${className}`.trim()} data-testid={testId} aria-busy={loading || undefined}>
      {hasHead && (
        <header className="panel-head">
          {title !== undefined && <h2>{title}</h2>}
          <div className="panel-actions">
            {loading && <Spinner />}
            {actions}
          </div>
        </header>
      )}
      {error ? <ErrorNote error={error} /> : null}
      {children}
    </section>
  )
}
