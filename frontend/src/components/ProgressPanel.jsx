import { Check, Globe, Loader2 } from 'lucide-react'
import { PIPELINE_STEPS, MODES } from '../constants'
import { useElapsed } from '../hooks/useMisc'
import { cx, formatElapsed } from '../utils'
import Orb from './Orb'

export default function ProgressPanel({ data }) {
  const elapsed = useElapsed(data.created_at, true)
  const progress = Math.max(2, Math.min(100, data.progress || 0))
  const activeIdx = PIPELINE_STEPS.reduce((acc, s, i) => (progress >= s.from ? i : acc), 0)
  const mode = MODES[data.mode]
  const queued = data.status === 'queued'

  return (
    <section className="glass animate-fade-up p-5 sm:p-7" aria-labelledby="progress-title">
      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="flex min-w-0 items-start gap-4">
          <Orb size="3.1rem" pulse className="mt-1" />
          <div className="min-w-0">
            <p className="font-sans text-xs font-semibold uppercase tracking-wider text-accent-hi">{mode?.label} in progress</p>
            <h1 id="progress-title" className="mt-1 text-xl font-bold leading-snug text-fg sm:text-2xl">{data.topic}</h1>
          </div>
        </div>
        <span className="chip tabular-nums" aria-label={`Elapsed time ${formatElapsed(elapsed)}`}>⏱ {formatElapsed(elapsed)}</span>
      </div>

      <div className="mt-6">
        <div className="mb-2 flex items-center justify-between gap-3 text-sm">
          <p aria-live="polite" className="flex min-w-0 items-center gap-2 font-medium text-fg">
            <Loader2 className="h-4 w-4 shrink-0 animate-spin text-accent-hi" aria-hidden="true" />
            <span className="truncate">{queued ? 'Queued…' : data.stage}</span>
          </p>
          <span className="tabular-nums text-fg-muted">{progress}%</span>
        </div>
        <div
          role="progressbar"
          aria-valuemin={0}
          aria-valuemax={100}
          aria-valuenow={progress}
          aria-label="Research progress"
          className="h-2.5 overflow-hidden rounded-full bg-fg/10"
        >
          <div className="h-full rounded-full bg-accent transition-[width] duration-700 ease-out" style={{ width: `${progress}%` }} />
        </div>
      </div>

      <ol className="mt-6 grid gap-2 sm:grid-cols-5" aria-label="Research stages">
        {PIPELINE_STEPS.map((s, i) => {
          const done = i < activeIdx
          const active = i === activeIdx
          return (
            <li
              key={s.label}
              aria-current={active ? 'step' : undefined}
              className={cx(
                'flex items-center gap-2 rounded-lg border px-3 py-2 text-[0.8rem] font-medium',
                done && 'border-ok/35 bg-ok/10 text-fg',
                active && 'border-accent/50 bg-accent/10 text-fg',
                !done && !active && 'border-line bg-fg/[0.04] text-fg-subtle',
              )}
            >
              <span className="grid h-5 w-5 shrink-0 place-items-center rounded-full border border-current text-[0.65rem]">
                {done ? <Check className="h-3 w-3" aria-hidden="true" /> : i + 1}
              </span>
              {s.label}
            </li>
          )
        })}
      </ol>

      {data.queries.length > 0 && (
        <div className="mt-6 animate-fade-up">
          <h2 className="font-sans text-xs font-bold uppercase tracking-wider text-fg-subtle">Search queries</h2>
          <ul className="mt-2 flex flex-wrap gap-2">
            {data.queries.map((q) => (
              <li key={q} className="chip !text-[0.78rem] !font-medium">{q}</li>
            ))}
          </ul>
        </div>
      )}

      {data.sources.length > 0 && (
        <div className="mt-6 animate-fade-up">
          <h2 className="font-sans text-xs font-bold uppercase tracking-wider text-fg-subtle">
            {data.sources.length} unique sources collected (duplicates removed)
          </h2>
          <ul className="mt-2 grid gap-2 sm:grid-cols-2">
            {data.sources.map((s) => (
              <li key={s.id} className="glass-soft flex items-center gap-2.5 px-3 py-2 text-sm">
                <Globe className="h-4 w-4 shrink-0 text-fg-subtle" aria-hidden="true" />
                <span className="chip chip-accent">{s.id}</span>
                <span className="truncate text-fg" title={s.title}>{s.domain}</span>
              </li>
            ))}
          </ul>
        </div>
      )}

      {data.warnings.length > 0 && (
        <ul className="mt-4 list-inside list-disc text-sm text-warn">
          {data.warnings.map((w) => <li key={w}>{w}</li>)}
        </ul>
      )}

      <p className="mt-6 text-xs text-fg-subtle">
        You can leave this page — the research keeps running and will appear under Recent when it’s done.
        {mode && <> Typical time: {mode.eta}.</>}
      </p>
    </section>
  )
}
