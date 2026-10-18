import type { AllocationResult } from '../api/models'
import { buildHeadline } from '../lib/headline'
import { Spinner } from './Panel'

interface HeadlineBannerProps {
  left: AllocationResult | undefined
  right: AllocationResult | undefined
  loading: boolean
}

/** The first thing a reviewer reads: how the two chosen algorithms differ, in plain words. */
export function HeadlineBanner({ left, right, loading }: HeadlineBannerProps) {
  const headline = left && right ? buildHeadline(left, right) : null
  return (
    <div className={`headline${headline?.same ? ' same' : ''}`} data-testid="headline" aria-live="polite">
      {headline ? (
        <p>
          <strong>{headline.title}:</strong> {headline.detail}
        </p>
      ) : (
        <p>Running the allocators…</p>
      )}
      {loading && <Spinner label="Updating" />}
    </div>
  )
}
