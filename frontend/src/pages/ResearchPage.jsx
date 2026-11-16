import { useEffect, useState } from 'react'
import { Loader2, Plus, SearchX } from 'lucide-react'
import { api } from '../services/api'
import { useResearch } from '../hooks/useResearch'
import ProgressPanel from '../components/ProgressPanel'
import ReportView from '../components/ReportView'
import { ErrorBanner } from '../components/Banners'

export default function ResearchPage({ id, navigate, onChanged }) {
  const { data, error, loading, reload, patchData } = useResearch(id)
  const [retrying, setRetrying] = useState(false)
  const [retryError, setRetryError] = useState(null)

  // Keep the sidebar's "Recent" list in sync when a job's status changes.
  useEffect(() => { if (data?.status) onChanged?.() }, [data?.status]) // eslint-disable-line react-hooks/exhaustive-deps

  async function retry() {
    setRetrying(true)
    setRetryError(null)
    try { await api.retry(id); reload() } catch (e) { setRetryError(e) } finally { setRetrying(false) }
  }

  if (error?.status === 404) {
    return (
      <div className="glass mx-auto mt-10 flex max-w-lg flex-col items-center gap-3 p-8 text-center">
        <SearchX className="h-9 w-9 text-fg-subtle" aria-hidden="true" />
        <h1 className="text-xl font-bold text-fg">Research not found</h1>
        <p className="text-sm text-fg-muted">It may have been deleted, or the link is wrong.</p>
        <a href="#/" className="btn btn-primary"><Plus className="h-4 w-4" aria-hidden="true" /> New research</a>
      </div>
    )
  }

  if (!data) {
    if (error) return <ErrorBanner className="mx-auto mt-10 max-w-2xl" title="Couldn’t load this research" error={error} onRetry={reload} />
    return (
      <div className="flex items-center justify-center gap-3 pt-24 text-fg-muted" role="status">
        <Loader2 className="h-5 w-5 animate-spin text-accent-hi" aria-hidden="true" /> Loading research…
      </div>
    )
  }

  if (data.status === 'queued' || data.status === 'running') {
    return (
      <div className="mx-auto flex max-w-4xl flex-col gap-4">
        {error && <ErrorBanner title="Lost connection to the backend (your research may still be running)" error={error} onRetry={reload} />}
        <ProgressPanel data={data} />
      </div>
    )
  }

  if (data.status === 'failed') {
    return (
      <div className="mx-auto flex max-w-3xl flex-col gap-4 pt-6">
        <div className="glass p-5 sm:p-7">
          <p className="text-xs font-semibold uppercase tracking-wider text-bad">Research failed</p>
          <h1 className="mt-1 text-xl font-bold text-fg sm:text-2xl">{data.topic}</h1>
          <p className="mt-2 text-sm text-fg-muted">No report was generated — nothing has been made up to fill the gap.</p>
          <ErrorBanner
            className="mt-5"
            title="What went wrong"
            error={data.error || { message: 'Unknown error' }}
            onRetry={retry}
            retrying={retrying}
          />
          {retryError && <ErrorBanner className="mt-3" title="Retry failed" error={retryError} />}
          <div className="mt-5 flex flex-wrap gap-2.5">
            <a href="#/" className="btn btn-ghost"><Plus className="h-4 w-4" aria-hidden="true" /> New research</a>
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="mx-auto max-w-3xl min-[1360px]:max-w-[64rem]">
      {error && <ErrorBanner className="mb-4" title="Connection problem" error={error} onRetry={reload} />}
      <ReportView data={data} patchData={patchData} onDeleted={() => { onChanged?.(); navigate('/history') }} />
    </div>
  )
}
