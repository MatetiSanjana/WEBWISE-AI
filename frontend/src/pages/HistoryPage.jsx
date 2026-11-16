import { useCallback, useEffect, useState } from 'react'
import { AlertTriangle, Bookmark, BookmarkCheck, CheckCircle2, Clock, Inbox, Loader2, Plus, Trash2 } from 'lucide-react'
import { api } from '../services/api'
import { MODES } from '../constants'
import { ErrorBanner } from '../components/Banners'
import { formatDate } from '../utils'

function StatusChip({ status }) {
  if (status === 'completed') return <span className="chip chip-ok"><CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Completed</span>
  if (status === 'failed') return <span className="chip chip-warn"><AlertTriangle className="h-3 w-3" aria-hidden="true" /> Failed</span>
  return <span className="chip "><Loader2 className="h-3 w-3 animate-spin" aria-hidden="true" /> In progress</span>
}

/** Used for both "Research History" (all runs) and "Saved Reports" (bookmarked ones). */
export default function HistoryPage({ saved, onChanged }) {
  const [items, setItems] = useState(null)
  const [error, setError] = useState(null)
  const [actionError, setActionError] = useState(null)
  const [confirmId, setConfirmId] = useState(null)

  const load = useCallback((signal) => {
    setError(null)
    api.history({ saved }, signal).then(setItems).catch((e) => { if (e?.name !== 'AbortError') setError(e) })
  }, [saved])

  useEffect(() => {
    setItems(null)
    const ctrl = new AbortController()
    load(ctrl.signal)
    return () => ctrl.abort()
  }, [load])

  async function toggleSaved(item) {
    setActionError(null)
    try {
      await api.setSaved(item.id, !item.saved)
      // In the Saved view, un-saving removes the row; elsewhere just flip the flag.
      setItems((list) => (saved ? list.filter((x) => x.id !== item.id) : list.map((x) => (x.id === item.id ? { ...x, saved: !x.saved } : x))))
      onChanged?.()
    } catch (e) { setActionError(e) }
  }

  async function remove(item) {
    setActionError(null)
    try {
      await api.remove(item.id)
      setItems((list) => list.filter((x) => x.id !== item.id))
      setConfirmId(null)
      onChanged?.()
    } catch (e) { setActionError(e) }
  }

  const title = saved ? 'Saved Reports' : 'Research History'

  return (
    <div className="mx-auto flex max-w-3xl flex-col gap-4 pt-4">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-2xl font-bold text-fg sm:text-3xl">{title}</h1>
        <a href="#/" className="btn btn-primary"><Plus className="h-4 w-4" aria-hidden="true" /> New research</a>
      </div>

      <ErrorBanner title="Couldn’t load your research" error={error} onRetry={() => load()} />
      <ErrorBanner title="That didn’t work" error={actionError} />

      {!items && !error && (
        <p className="flex items-center gap-2 text-fg-muted" role="status"><Loader2 className="h-4 w-4 animate-spin text-accent-hi" aria-hidden="true" /> Loading…</p>
      )}

      {items && items.length === 0 && (
        <div className="glass flex flex-col items-center gap-3 p-10 text-center">
          <Inbox className="h-9 w-9 text-fg-subtle" aria-hidden="true" />
          <p className="font-semibold text-fg">{saved ? 'No saved reports yet' : 'No research yet'}</p>
          <p className="max-w-sm text-sm text-fg-muted">
            {saved ? 'Open a finished report and press “Save report” to keep it here.' : 'Start your first research and it will show up here.'}
          </p>
        </div>
      )}

      {items && items.length > 0 && (
        <ul className="flex flex-col gap-3">
          {items.map((item) => (
            <li key={item.id} className="glass animate-fade-up p-4">
              <a href={`#/research/${item.id}`} className="block rounded-lg">
                <h2 className="font-semibold leading-snug text-fg hover:text-accent-hi">{item.title || item.topic}</h2>
                {item.title && <p className="mt-0.5 line-clamp-1 text-sm text-fg-subtle">{item.topic}</p>}
              </a>
              <div className="mt-3 flex flex-wrap items-center gap-2 text-xs">
                <StatusChip status={item.status} />
                <span className="chip">{MODES[item.mode]?.label ?? item.mode}</span>
                {item.sources_count > 0 && <span className="chip">{item.sources_count} sources</span>}
                <span className="flex items-center gap-1 text-fg-subtle"><Clock className="h-3 w-3" aria-hidden="true" /> {formatDate(item.created_at)}</span>
                <span className="ml-auto flex items-center gap-1.5">
                  <button
                    type="button"
                    className="btn btn-ghost !min-h-10 !px-3"
                    onClick={() => toggleSaved(item)}
                    aria-pressed={item.saved}
                    aria-label={item.saved ? `Remove “${item.title || item.topic}” from saved` : `Save “${item.title || item.topic}”`}
                  >
                    {item.saved ? <BookmarkCheck className="h-4 w-4 text-accent-hi" aria-hidden="true" /> : <Bookmark className="h-4 w-4" aria-hidden="true" />}
                  </button>
                  {confirmId === item.id ? (
                    <>
                      <button type="button" className="btn btn-danger !min-h-10 !px-3" onClick={() => remove(item)}>Delete</button>
                      <button type="button" className="btn btn-ghost !min-h-10 !px-3" onClick={() => setConfirmId(null)}>Cancel</button>
                    </>
                  ) : (
                    <button type="button" className="btn btn-ghost !min-h-10 !px-3" onClick={() => setConfirmId(item.id)} aria-label={`Delete “${item.title || item.topic}”`}>
                      <Trash2 className="h-4 w-4" aria-hidden="true" />
                    </button>
                  )}
                </span>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
