import { AlertTriangle, Info, Loader2, RotateCcw, ServerCrash } from 'lucide-react'
import { cx } from '../utils'

export function ErrorBanner({ title = 'Something went wrong', error, onRetry, retrying, className }) {
  if (!error) return null
  return (
    <div role="alert" className={cx('flex flex-col gap-3 rounded-xl border border-bad/40 bg-bad/10 p-4 sm:flex-row sm:items-start', className)}>
      <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-bad" aria-hidden="true" />
      <div className="min-w-0 flex-1">
        <p className="font-semibold text-fg">{title}</p>
        <p className="mt-0.5 break-words text-sm text-fg-muted">{error.message}</p>
        {error.code && <p className="mt-1 text-xs text-fg-subtle">Error code: {error.code}</p>}
      </div>
      {onRetry && (
        <button type="button" className="btn btn-danger shrink-0" onClick={onRetry} disabled={retrying}>
          {retrying ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <RotateCcw className="h-4 w-4" aria-hidden="true" />}
          Retry
        </button>
      )}
    </div>
  )
}

export function InfoBanner({ tone = 'amber', icon: Icon = Info, title, children, className }) {
  const tones = {
    amber: 'border-warn/40 bg-warn/10 text-fg',
    blue: 'border-line-strong bg-raised text-fg',
  }
  return (
    <div role="note" className={cx('flex gap-3 rounded-xl border p-3.5 text-sm', tones[tone], className)}>
      <Icon className="mt-0.5 h-[1.1rem] w-[1.1rem] shrink-0" aria-hidden="true" />
      <div className="min-w-0">
        {title && <p className="font-semibold">{title}</p>}
        <div className="opacity-90">{children}</div>
      </div>
    </div>
  )
}

/** Shown on the home page when the backend is unreachable or missing its API keys. */
export function HealthBanner({ health, error, onRefresh }) {
  if (error) {
    return (
      <div role="alert" className="flex items-start gap-3 rounded-xl border border-bad/40 bg-bad/10 p-3.5 text-sm text-fg">
        <ServerCrash className="mt-0.5 h-5 w-5 shrink-0" aria-hidden="true" />
        <div className="flex-1">
          <p className="font-semibold">Backend unreachable</p>
          <p className="opacity-90">{error.message}</p>
        </div>
        <button type="button" className="btn btn-danger !min-h-9 !px-3" onClick={onRefresh}>Check again</button>
      </div>
    )
  }
  if (health && health.status !== 'ok') {
    const missing = [!health.tavily_configured && 'TAVILY_API_KEY', !health.gemini_configured && 'GEMINI_API_KEY'].filter(Boolean)
    return (
      <InfoBanner title="Backend is missing configuration">
        Add {missing.join(' and ')} to the <code className="rounded bg-black/30 px-1">.env</code> file and restart the backend. Research can’t start until then.
      </InfoBanner>
    )
  }
  return null
}
