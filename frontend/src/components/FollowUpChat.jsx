import { useEffect, useRef, useState } from 'react'
import { CheckCircle2, HelpCircle, Loader2, MessageSquare, Quote, Send, ShieldAlert, XCircle } from 'lucide-react'
import { api } from '../services/api'
import { FOLLOW_UP_IDEAS } from '../constants'
import CitationText, { CiteList } from './CitationText'
import { ErrorBanner } from './Banners'
import { Section } from './ReportParts'
import { cx } from '../utils'

// Colour here carries meaning: the left rule + chip tell you how well the answer is backed by the sources.
const ANSWER_META = {
  evidence_based: { text: 'Evidence-based', cls: 'chip-ok', rule: 'border-l-ok', icon: CheckCircle2, note: 'Supported by the cited sources from this research.' },
  partially_supported: { text: 'Partially supported', cls: 'chip-warn', rule: 'border-l-warn', icon: HelpCircle, note: 'Only part of this answer is backed by the cited sources.' },
  not_in_research: { text: 'Not found in this research', cls: '', rule: 'border-l-fg-subtle', icon: XCircle, note: 'The collected sources do not cover this. Start a new research to look into it.' },
  unsupported: { text: 'Unsupported', cls: 'chip-bad', rule: 'border-l-bad', icon: ShieldAlert, note: 'No valid citation backs this answer. Do not rely on it.' },
}

function UserBubble({ children }) {
  return (
    <div className="ml-auto max-w-[92%] rounded-2xl rounded-br-sm border border-line-strong bg-hover px-4 py-2.5 text-[0.95rem] leading-relaxed text-fg sm:max-w-[80%]">
      {children}
    </div>
  )
}

function Answer({ turn, sources, onCite }) {
  const meta = ANSWER_META[turn.answer_type] || ANSWER_META.unsupported
  const Icon = meta.icon
  return (
    <div className="flex flex-col gap-3">
      <UserBubble>{turn.question}</UserBubble>
      <div data-testid="answer" className={cx('rounded-xl border border-l-[3px] border-line bg-raised p-4', meta.rule)}>
        <div className="mb-2.5 flex flex-wrap items-center gap-x-3 gap-y-1.5">
          <span className="text-[0.68rem] font-bold uppercase tracking-[0.14em] text-fg-subtle">Webwise AI</span>
          <span className={cx('chip', meta.cls)}><Icon className="h-3 w-3" aria-hidden="true" /> {meta.text}</span>
        </div>
        <p className="whitespace-pre-line text-[0.95rem] leading-relaxed text-fg">
          <CitationText text={turn.answer} sources={sources} onCite={onCite} />
        </p>
        {turn.source_ids?.length > 0 && (
          <p className="mt-3 flex flex-wrap items-center gap-1.5 text-xs text-fg-subtle">Sources: <CiteList ids={turn.source_ids} sources={sources} onCite={onCite} /></p>
        )}
        {turn.quote_verified && turn.supporting_quote && (
          <blockquote className="mt-3 flex gap-2 border-l-2 border-accent/50 pl-3 font-serif text-[1.02rem] italic leading-snug text-fg-muted">
            <Quote className="mt-1 h-3 w-3 shrink-0 text-accent-hi" aria-hidden="true" />
            “{turn.supporting_quote}”
          </blockquote>
        )}
        <p className="mt-3 text-xs text-fg-subtle">{meta.note}</p>
        {turn.note && <p className="mt-1 text-xs text-warn">{turn.note}</p>}
      </div>
    </div>
  )
}

export default function FollowUpChat({ data, sources, onCite, patchData }) {
  const [question, setQuestion] = useState('')
  const [pending, setPending] = useState(null)
  const [error, setError] = useState(null)
  const endRef = useRef(null)
  const turns = data.follow_ups

  // Scroll to the newest message only when one ARRIVES, not on first load (opening a report that already has a
  // conversation must not jump the page to the bottom).
  const seen = useRef(turns.length)
  useEffect(() => {
    if (pending || turns.length > seen.current) endRef.current?.scrollIntoView({ block: 'nearest' })
    seen.current = turns.length
  }, [pending, turns.length])

  async function ask(q) {
    const text = (q ?? question).trim()
    if (text.length < 3 || pending) return
    setError(null)
    setPending(text)
    setQuestion('')
    try {
      const answer = await api.followUp(data.id, text)
      patchData((d) => ({ ...d, follow_ups: [...d.follow_ups, answer] }))
    } catch (e) {
      setError(e)
      setQuestion(text) // give the question back so the user can retry
    } finally {
      setPending(null)
    }
  }

  return (
    <Section id="followup" title="Ask a follow-up" icon={MessageSquare}>
      <p className="mb-5 text-sm text-fg-muted">
        Answers use only the sources collected for this research. If they don’t cover your question, you’ll be told so instead of getting a guess.
      </p>

      <div className="flex flex-col gap-5" aria-live="polite">
        {turns.map((t, i) => <Answer key={i} turn={t} sources={sources} onCite={onCite} />)}
        {pending && (
          <div className="flex flex-col gap-3">
            <UserBubble>{pending}</UserBubble>
            <div className="flex items-center gap-2 text-sm text-fg-muted"><Loader2 className="h-4 w-4 animate-spin text-accent-hi" aria-hidden="true" /> Checking the sources…</div>
          </div>
        )}
        <div ref={endRef} />
      </div>

      {error && <ErrorBanner className="mt-3" title="Couldn’t get an answer" error={error} onRetry={() => ask(question)} />}

      {turns.length === 0 && !pending && (
        <div className="mb-3 flex flex-wrap gap-2">
          {FOLLOW_UP_IDEAS.map((idea) => (
            <button
              key={idea}
              type="button"
              className="cursor-pointer rounded-full border border-line-strong px-3.5 py-1.5 text-[0.82rem] text-fg-muted transition-colors hover:border-accent/50 hover:bg-accent/10 hover:text-fg"
              onClick={() => ask(idea)}
            >
              {idea}
            </button>
          ))}
        </div>
      )}

      <form
        className="mt-3 flex items-end gap-2 rounded-xl border border-line-strong bg-raised p-2 transition-colors focus-within:border-accent/60"
        onSubmit={(e) => { e.preventDefault(); ask() }}
      >
        <label htmlFor="followup-input" className="sr-only">Your follow-up question</label>
        <textarea
          id="followup-input"
          rows={1}
          value={question}
          maxLength={1000}
          onChange={(e) => setQuestion(e.target.value)}
          onKeyDown={(e) => { if (e.key === 'Enter' && !e.shiftKey) { e.preventDefault(); ask() } }}
          placeholder="Ask about this research…"
          disabled={!!pending}
          className="min-h-11 flex-1 resize-none bg-transparent px-2.5 py-2.5 text-[0.95rem] text-fg outline-none placeholder:text-fg-subtle focus-visible:outline-none disabled:opacity-60"
        />
        <button type="submit" className="btn btn-primary !min-h-11 !w-11 !px-0" disabled={question.trim().length < 3 || !!pending} aria-label="Send question">
          <Send className="h-4 w-4" aria-hidden="true" />
        </button>
      </form>
    </Section>
  )
}
