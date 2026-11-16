import { AlertTriangle, CheckCircle2, ExternalLink, Quote, Scale } from 'lucide-react'
import CitationText from './CitationText'
import { cx, displayUrl, safeHref } from '../utils'

export const TYPE_LABEL = {
  fact: { text: 'Fact', cls: 'chip-accent' },
  opinion: { text: 'Opinion', cls: '' },
  prediction: { text: 'Prediction', cls: '' },
}

// Deliberately never says "verified": we show how many site domains are cited and whether the quote was found.
export const SUPPORT_LABEL = {
  multi_source: { text: 'Cited by multiple sites', cls: 'chip-ok' },
  single_source: { text: 'Single source site', cls: '' },
  quote_unverified: { text: 'Quote not located in source', cls: 'chip-warn' },
}

export function Section({ id, title, icon: Icon, children, count, className }) {
  return (
    <section id={`sec-${id}`} tabIndex={-1} aria-labelledby={`h-${id}`} className={cx('glass scroll-mt-32 p-5 outline-none sm:p-6 lg:scroll-mt-20', className)}>
      <h2 id={`h-${id}`} className="mb-3 flex items-center gap-2.5 text-lg font-bold text-fg">
        {Icon && <Icon className="h-5 w-5 text-accent-hi" aria-hidden="true" />}
        {title}
        {count != null && <span className="chip">{count}</span>}
      </h2>
      {children}
    </section>
  )
}

export function FindingCard({ finding, index, sources, onCite }) {
  const type = TYPE_LABEL[finding.claim_type] || TYPE_LABEL.fact
  const support = SUPPORT_LABEL[finding.support_level] || SUPPORT_LABEL.single_source
  return (
    <article className="glass-soft p-4" aria-label={`Key finding ${index + 1}`}>
      <div className="mb-2 flex flex-wrap items-center gap-2">
        <span className="grid h-6 w-6 place-items-center rounded-md bg-accent text-xs font-bold text-on-accent">{index + 1}</span>
        <span className={cx('chip', type.cls)}>{type.text}</span>
        <span className={cx('chip', support.cls)}>{support.text}</span>
      </div>
      <p className="leading-relaxed text-fg">
        <CitationText text={finding.statement} sources={sources} onCite={onCite} />
      </p>
      {finding.quote_verified && finding.supporting_quote && (
        <blockquote className="mt-3 flex gap-2.5 border-l-2 border-accent/50 pl-3 text-[0.85rem] italic text-fg-muted">
          <Quote className="mt-0.5 h-3.5 w-3.5 shrink-0 text-accent-hi" aria-hidden="true" />
          <span>
            “{finding.supporting_quote}”
            <span className="mt-1 flex items-center gap-1 text-[0.72rem] not-italic text-ok">
              <CheckCircle2 className="h-3 w-3" aria-hidden="true" /> Quote located in the cited source text
            </span>
          </span>
        </blockquote>
      )}
    </article>
  )
}

export function SourceCard({ source, cited }) {
  const href = safeHref(source.url)
  const date = source.published_date
  return (
    <article
      id={`source-${source.id}`}
      tabIndex={-1}
      className="glass-soft flex flex-col gap-2 p-4 scroll-mt-24"
      aria-label={`Source ${source.id}: ${source.title}`}
    >
      <div className="flex flex-wrap items-center gap-2">
        <span className="chip chip-accent">{source.id}</span>
        <span className={cx('chip', cited ? 'chip-ok' : '')}>{cited ? 'Cited in report' : 'Retrieved, not cited'}</span>
      </div>
      <h3 className="font-semibold leading-snug text-fg">
        {href ? (
          <a href={href} target="_blank" rel="noopener noreferrer" className="inline-flex items-start gap-1.5 break-words hover:text-accent-hi hover:underline">
            {source.title}
            <ExternalLink className="mt-1 h-3.5 w-3.5 shrink-0" aria-label="(opens in a new tab)" />
          </a>
        ) : (
          source.title
        )}
      </h3>
      <p className="text-xs text-fg-muted">
        <span className="font-medium">{source.domain}</span> · <span className={date === 'Date unavailable' ? 'italic text-fg-subtle' : ''}>{date}</span>
      </p>
      {source.snippet && <p className="line-clamp-3 text-[0.82rem] leading-relaxed text-fg-muted">{source.snippet}</p>}
      {href && <a href={href} target="_blank" rel="noopener noreferrer" title={source.url} className="block truncate text-[0.74rem] text-fg-subtle hover:text-accent-hi hover:underline">{displayUrl(source.url)}</a>}
      {source.relevance_score != null && (
        <p className="text-[0.7rem] text-fg-subtle" title="Search-engine relevance to the query. It says nothing about how reliable the source is.">
          Search relevance {source.relevance_score.toFixed(2)} · not a credibility rating
        </p>
      )}
    </article>
  )
}

export function ConflictBlock({ conflict, sources, onCite }) {
  return (
    <article className="glass-soft p-4">
      <h3 className="mb-3 flex items-center gap-2 font-semibold text-fg">
        <Scale className="h-4 w-4 text-warn" aria-hidden="true" /> {conflict.topic}
      </h3>
      <div className="grid gap-3 md:grid-cols-2">
        {conflict.positions.map((p, i) => (
          <div key={i} className="rounded-lg border border-line bg-black/20 p-3 text-sm leading-relaxed text-fg">
            <span className="mb-1 block text-[0.7rem] font-semibold uppercase tracking-wider text-fg-subtle">Position {i + 1}</span>
            <CitationText text={p.summary} sources={sources} onCite={onCite} />
          </div>
        ))}
      </div>
      {conflict.assessment && (
        <p className="mt-3 text-sm italic text-fg-muted">
          <CitationText text={conflict.assessment} sources={sources} onCite={onCite} />
        </p>
      )}
    </article>
  )
}

export function Uncited() {
  return (
    <span className="chip chip-warn ml-2 align-middle" title="The model gave this text without a valid citation">
      <AlertTriangle className="h-3 w-3" aria-hidden="true" /> uncited
    </span>
  )
}
