import { useCallback, useMemo, useState } from 'react'
import {
  AlertTriangle, BookOpen, Bookmark, BookmarkCheck, Check, Download, FileText, Flag, Layers, Link2, Loader2,
  ListChecks, ShieldCheck, Target, Trash2, Sparkles, Hourglass,
} from 'lucide-react'
import { api } from '../services/api'
import { usePrefersReducedMotion } from '../hooks/useMisc'
import { MODES } from '../constants'
import { formatDate } from '../utils'
import CitationText from './CitationText'
import { ErrorBanner, InfoBanner } from './Banners'
import { ConflictBlock, FindingCard, Section, SourceCard, Uncited } from './ReportParts'
import FollowUpChat from './FollowUpChat'
import SectionNav, { REPORT_SECTIONS, useScrollSpy } from './SectionNav'

export default function ReportView({ data, onChanged, onDeleted, patchData }) {
  const { report, sources, id } = data
  const reduced = usePrefersReducedMotion()
  const [busy, setBusy] = useState({ pdf: false, save: false, del: false })
  const [error, setError] = useState(null)
  const [confirmDelete, setConfirmDelete] = useState(false)
  const cited = useMemo(() => new Set(report.references.filter((r) => r.cited).map((r) => r.id)), [report])
  const cr = report.citation_report
  const [activeSection, setActiveSection] = useScrollSpy(REPORT_SECTIONS.map((x) => x.id))

  const jumpToSection = useCallback((sid) => {
    const el = document.getElementById(`sec-${sid}`)
    if (!el) return
    el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'start' })
    el.focus({ preventScroll: true })
    setActiveSection(sid)
  }, [reduced, setActiveSection])

  const jumpToSource = useCallback((sid) => {
    const el = document.getElementById(`source-${sid}`)
    if (!el) return
    el.scrollIntoView({ behavior: reduced ? 'auto' : 'smooth', block: 'center' })
    el.focus({ preventScroll: true })
    el.classList.remove('source-flash')
    void el.offsetWidth // restart the animation
    el.classList.add('source-flash')
  }, [reduced])

  async function run(key, fn) {
    setBusy((b) => ({ ...b, [key]: true }))
    setError(null)
    try { await fn() } catch (e) { setError(e) } finally { setBusy((b) => ({ ...b, [key]: false })) }
  }

  const cite = (text) => <CitationText text={text} sources={sources} onCite={jumpToSource} />

  return (
    <div className="min-[1360px]:grid min-[1360px]:grid-cols-[minmax(0,48rem)_12.5rem] min-[1360px]:justify-center min-[1360px]:gap-10">
    <article className="flex min-w-0 flex-col gap-5" aria-labelledby="report-title">
      <header className="glass animate-fade-up p-5 sm:p-7">
        <div className="flex flex-wrap items-center gap-2 text-xs">
          <span className="chip ">{MODES[report.mode]?.label}</span>
          <span className="chip">{sources.length} sources</span>
          <span className="chip" title="Model that wrote this analysis">{report.model}</span>
          <span className="text-fg-subtle">{formatDate(report.generated_at)}</span>
        </div>
        <h1 id="report-title" className="mt-3 text-2xl font-bold leading-tight text-fg sm:text-3xl">{report.title}</h1>
        <p className="mt-1 text-sm text-fg-subtle">Topic: {data.topic}</p>

        <div className="mt-5 flex flex-wrap gap-2.5">
          <button type="button" className="btn btn-primary" disabled={busy.pdf} onClick={() => run('pdf', () => api.downloadPdf(id))}>
            {busy.pdf ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Download className="h-4 w-4" aria-hidden="true" />}
            Download PDF
          </button>
          <button
            type="button"
            className="btn btn-ghost"
            aria-pressed={data.saved}
            disabled={busy.save}
            onClick={() => run('save', async () => {
              const next = await api.setSaved(id, !data.saved)
              patchData((d) => ({ ...d, saved: next.saved }))
            })}
          >
            {data.saved ? <BookmarkCheck className="h-4 w-4 text-accent-hi" aria-hidden="true" /> : <Bookmark className="h-4 w-4" aria-hidden="true" />}
            {data.saved ? 'Saved' : 'Save report'}
          </button>
          {confirmDelete ? (
            <span className="flex items-center gap-2" role="group" aria-label="Confirm delete">
              <button type="button" className="btn btn-danger" disabled={busy.del} onClick={() => run('del', async () => { await api.remove(id); onDeleted() })}>
                {busy.del ? <Loader2 className="h-4 w-4 animate-spin" aria-hidden="true" /> : <Check className="h-4 w-4" aria-hidden="true" />} Delete permanently
              </button>
              <button type="button" className="btn btn-ghost" onClick={() => setConfirmDelete(false)}>Cancel</button>
            </span>
          ) : (
            <button type="button" className="btn btn-ghost" onClick={() => setConfirmDelete(true)}>
              <Trash2 className="h-4 w-4" aria-hidden="true" /> Delete
            </button>
          )}
        </div>
        {error && <ErrorBanner className="mt-4" title="That didn’t work" error={error} />}
      </header>

      <SectionNav variant="bar" active={activeSection} onJump={jumpToSection} />

      <InfoBanner tone="blue" icon={ShieldCheck} title="How to read this report">
        {report.disclaimer}
      </InfoBanner>

      {report.insufficient_evidence && (
        <InfoBanner title="Insufficient evidence found.">
          The retrieved sources were too thin to answer this topic reliably. Treat everything below as incomplete, or try rephrasing the topic or using Deep Research.
        </InfoBanner>
      )}

      <Section id="summary" title="Executive Summary" icon={Sparkles}>
        <p className="prose-report">{cite(report.executive_summary)}</p>
      </Section>

      <Section id="objective" title="Research Objective" icon={Target}>
        <p className="prose-report">{report.objective}</p>
        {report.queries?.length > 0 && (
          <p className="mt-3 flex flex-wrap items-center gap-2 text-xs text-fg-subtle">
            Searched for:
            {report.queries.map((q) => <span key={q} className="chip">{q}</span>)}
          </p>
        )}
      </Section>

      <Section id="findings" title="Key Findings" icon={ListChecks} count={report.key_findings.length}>
        {report.key_findings.length ? (
          <div className="grid gap-3">
            {report.key_findings.map((f, i) => <FindingCard key={i} finding={f} index={i} sources={sources} onCite={jumpToSource} />)}
          </div>
        ) : (
          <p className="text-fg-muted">Insufficient evidence found.</p>
        )}
        {report.unsupported_claims.length > 0 && (
          <details className="mt-4 rounded-lg border border-warn/35 bg-warn/5 p-3 text-sm text-fg">
            <summary className="cursor-pointer font-medium">
              {report.unsupported_claims.length} claim(s) excluded because they had no valid citation
            </summary>
            <ul className="mt-2 list-inside list-disc text-fg-muted">
              {report.unsupported_claims.map((c, i) => <li key={i}>{c.statement}</li>)}
            </ul>
          </details>
        )}
      </Section>

      <Section id="analysis" title="Detailed Analysis" icon={BookOpen}>
        {report.detailed_analysis.length ? (
          <div className="flex flex-col gap-5">
            {report.detailed_analysis.map((s, i) => (
              <div key={i}>
                <h3 className="font-semibold text-fg">{s.heading}{s.uncited && <Uncited />}</h3>
                <p className="prose-report mt-1.5">{cite(s.body)}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-fg-muted">Insufficient evidence found.</p>}
      </Section>

      <Section id="comparison" title="Comparison of Findings" icon={Layers}>
        {report.comparison.length ? (
          <div className="flex flex-col gap-4">
            {report.comparison.map((c, i) => (
              <div key={i} className="glass-soft p-4">
                <h3 className="font-semibold text-fg">{c.topic}{c.uncited && <Uncited />}</h3>
                <p className="prose-report mt-1.5">{cite(c.summary)}</p>
              </div>
            ))}
          </div>
        ) : <p className="text-fg-muted">No cross-source comparison could be supported by the retrieved evidence.</p>}
      </Section>

      <Section id="conflicts" title="Conflicting Information" icon={Flag} count={report.conflicts.length}>
        {report.conflicts.length ? (
          <div className="flex flex-col gap-4">
            {report.conflicts.map((c, i) => <ConflictBlock key={i} conflict={c} sources={sources} onCite={jumpToSource} />)}
          </div>
        ) : <p className="text-fg-muted">No conflicting information was identified between the retrieved sources.</p>}
        {report.outdated_info.length > 0 && (
          <div className="mt-5">
            <h3 className="mb-2 flex items-center gap-2 font-semibold text-fg"><Hourglass className="h-4 w-4 text-warn" aria-hidden="true" /> Possibly outdated information</h3>
            <ul className="flex flex-col gap-3">
              {report.outdated_info.map((o, i) => (
                <li key={i} className="glass-soft p-3 text-sm leading-relaxed text-fg">
                  {cite(o.statement)}
                  <span className="mt-1 block text-fg-subtle">Why: {cite(o.reason)}</span>
                </li>
              ))}
            </ul>
          </div>
        )}
      </Section>

      <Section id="limitations" title="Limitations and Evidence Gaps" icon={AlertTriangle}>
        {report.limitations.length ? (
          <ul className="prose-report list-inside list-disc space-y-2">
            {report.limitations.map((l, i) => <li key={i}>{cite(l)}</li>)}
          </ul>
        ) : <p className="text-fg-muted">None identified by the analysis — this does not mean none exist.</p>}
        <p className="mt-4 rounded-lg bg-black/20 p-3 text-xs text-fg-muted">
          <strong className="text-fg">Citation check:</strong>{' '}
          {cr.findings_quote_verified} of {cr.findings_total} key findings have a quote located in the cited source text;{' '}
          {cr.invalid_ids_removed + cr.invalid_inline_markers_removed} invalid citation(s) were removed automatically.
        </p>
      </Section>

      <Section id="conclusion" title="Conclusion" icon={FileText}>
        <p className="prose-report">{cite(report.conclusion)}</p>
      </Section>

      <Section id="sources" title="References" icon={Link2} count={sources.length}>
        <div className="grid gap-3 md:grid-cols-2">
          {sources.map((s) => <SourceCard key={s.id} source={s} cited={cited.has(s.id)} />)}
        </div>
      </Section>

      <FollowUpChat data={data} sources={sources} onCite={jumpToSource} patchData={patchData} />
    </article>
    <SectionNav variant="rail" active={activeSection} onJump={jumpToSection} />
    </div>
  )
}
