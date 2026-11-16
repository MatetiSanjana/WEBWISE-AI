import { Fragment } from 'react'

// Matches "[S3]" and also bare "S3" (models often write "According to S3 ..."). A bare token only becomes a
// chip when it matches a real source ID, so ordinary words are never touched.
const MARKER = /(\[S\d+\]|\bS\d{1,3}\b)/g

/**
 * Renders text with inline [S#] markers as clickable citation chips.
 * Text is rendered as plain React text nodes (never as HTML), so source/LLM content cannot inject markup.
 * Markers that don't match a real source are shown as plain text rather than as a chip.
 */
export default function CitationText({ text, sources, onCite, className }) {
  if (!text) return null
  const byId = new Map((sources || []).map((s) => [s.id, s]))
  return (
    <span className={className}>
      {text.split(MARKER).map((part, i) => {
        const m = /^\[?(S\d+)\]?$/.exec(part)
        if (!m) return <Fragment key={i}>{part}</Fragment>
        const src = byId.get(m[1])
        if (!src) return <Fragment key={i}>{part}</Fragment>
        return (
          <button
            key={i}
            type="button"
            className="cite"
            onClick={() => onCite?.(m[1])}
            title={`${src.domain} — ${src.title}`}
            aria-label={`Source ${m[1]}: ${src.title}. Jump to source`}
          >
            {m[1]}
          </button>
        )
      })}
    </span>
  )
}

/** A row of citation chips for a list of source IDs (used under findings/answers). */
export function CiteList({ ids, sources, onCite }) {
  if (!ids?.length) return null
  return (
    <span className="inline-flex flex-wrap items-center gap-1">
      {ids.map((id) => {
        const src = sources?.find((s) => s.id === id)
        return (
          <button key={id} type="button" className="cite" onClick={() => onCite?.(id)} title={src ? `${src.domain} — ${src.title}` : id} aria-label={`Jump to source ${id}`}>
            {id}
          </button>
        )
      })}
    </span>
  )
}
