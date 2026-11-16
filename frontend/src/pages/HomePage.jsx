import { useRef, useState } from 'react'
import {
  ArrowLeftRight, ArrowUp, BatteryCharging, HeartPulse, Landmark, Loader2, Newspaper, Scale, Sparkles,
} from 'lucide-react'
import { api } from '../services/api'
import { useSettings } from '../hooks/useSettings'
import { useHealth } from '../hooks/useMisc'
import { MODES, QUICK_STARTERS, SUGGESTION_CARDS } from '../constants'
import ModeSelector from '../components/ModeSelector'
import Orb from '../components/Orb'
import { ErrorBanner, HealthBanner } from '../components/Banners'
import { cx } from '../utils'

const MIN = 5
const MAX = 500

const STARTER_ICONS = { news: Newspaper, scale: Scale, compare: ArrowLeftRight }
const CARD_ICONS = { battery: BatteryCharging, heart: HeartPulse, landmark: Landmark }

export default function HomePage({ navigate, onStarted }) {
  const { settings } = useSettings()
  const { health, error: healthError, refresh } = useHealth()
  const [topic, setTopic] = useState('')
  const [mode, setMode] = useState(settings.defaultMode)
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState(null)
  const [showHint, setShowHint] = useState(false)
  const inputRef = useRef(null)

  const trimmed = topic.trim()
  const valid = trimmed.length >= MIN && trimmed.length <= MAX

  async function start() {
    if (submitting) return
    if (!valid) {
      // The button always looks usable. Pressing it with no topic guides the user instead of doing nothing.
      setShowHint(true)
      inputRef.current?.focus()
      return
    }
    setSubmitting(true)
    setError(null)
    try {
      const { research_id } = await api.startResearch(trimmed, mode)
      onStarted?.()
      navigate(`/research/${research_id}`)
    } catch (e) {
      setError(e)
    } finally {
      setSubmitting(false)
    }
  }

  function focusEnd(text) {
    requestAnimationFrame(() => {
      const el = inputRef.current
      if (!el) return
      el.focus()
      el.setSelectionRange(text.length, text.length)
    })
  }

  function applyStarter(prefix) {
    setError(null)
    setShowHint(false)
    if (trimmed.length === 0) {
      setTopic(prefix)
      focusEnd(prefix)
    } else {
      inputRef.current?.focus() // don't overwrite what the user already typed
    }
  }

  function pickSuggestion(t) {
    setTopic(t)
    setError(null)
    setShowHint(false)
    focusEnd(t)
  }

  const m = MODES[mode]

  return (
    <div className="mx-auto flex w-full max-w-[50rem] flex-col items-center pt-2 sm:pt-8">
      <div className="animate-fade-up flex flex-col items-center text-center">
        <Orb className="mb-8 mt-2" />
        <h1
          id="home-title"
          className="font-sans text-[2.4rem] font-normal leading-[1.1] tracking-[-0.025em] text-fg sm:text-[3.4rem]"
        >
          What would you like to <em className="font-serif font-medium italic text-accent-hi">research?</em>
        </h1>
        <p className="mt-5 max-w-xl text-[1.02rem] leading-relaxed text-fg-muted">
          Webwise AI searches the live web, reads multiple sources, compares what they say, and writes a cited report — flagging where sources disagree or the evidence is thin.
        </p>
      </div>

      <div className="mt-8 w-full">
        <HealthBanner health={health} error={healthError} onRefresh={refresh} />
      </div>

      <div className="mt-8 flex w-full flex-wrap justify-center gap-2.5">
        {QUICK_STARTERS.map((s) => {
          const Icon = STARTER_ICONS[s.icon]
          return (
            <button
              key={s.label}
              type="button"
              onClick={() => applyStarter(s.prefix)}
              className="inline-flex min-h-10 cursor-pointer items-center gap-2 rounded-full border border-line-strong bg-white/[0.04] px-4 text-sm text-fg-muted transition-colors hover:bg-white/[0.09] hover:text-fg"
            >
              <Icon className="h-4 w-4 text-accent-hi" aria-hidden="true" /> {s.label}
            </button>
          )
        })}
      </div>

      <form
        className="animate-fade-up mt-4 w-full rounded-[1.6rem] border border-line-strong bg-white/[0.045] transition-[border-color,box-shadow] focus-within:border-accent/60 focus-within:shadow-[0_0_0_4px_rgb(167_139_250/0.12)]"
        aria-labelledby="home-title"
        onSubmit={(e) => { e.preventDefault(); start() }}
      >
        <div className="flex gap-3 px-5 pt-5">
          <Sparkles className="mt-1 h-5 w-5 shrink-0 text-accent-hi" aria-hidden="true" />
          <div className="min-w-0 flex-1">
            <label htmlFor="topic" className="sr-only">Research topic or question</label>
            <textarea
              id="topic"
              ref={inputRef}
              value={topic}
              onChange={(e) => { setTopic(e.target.value); setShowHint(false) }}
              onKeyDown={(e) => { if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) { e.preventDefault(); start() } }}
              rows={3}
              maxLength={MAX}
              placeholder="Ask a question or describe a topic…"
              className="w-full resize-none bg-transparent text-[1.08rem] leading-relaxed text-fg outline-none placeholder:text-fg-subtle focus-visible:outline-none"
              aria-describedby="topic-help"
              disabled={submitting}
            />
          </div>
        </div>

        <p id="topic-help" className="flex justify-between px-5 pb-1 text-xs text-fg-subtle">
          <span aria-live="polite" className={cx(showHint && !valid && 'font-semibold text-warn')}>
            {showHint && !valid
              ? `Tell me what to research first — at least ${MIN} characters.`
              : trimmed.length > 0 && trimmed.length < MIN ? `At least ${MIN} characters` : 'Ctrl / ⌘ + Enter to start'}
          </span>
          <span className={cx('tabular-nums', trimmed.length > MAX - 40 && 'text-warn')}>{topic.length}/{MAX}</span>
        </p>

        <div className="flex items-center justify-between gap-3 border-t border-line px-3 py-3">
          <ModeSelector value={mode} onChange={setMode} disabled={submitting} />
          <button
            type="submit"
            className="btn btn-primary !h-11 !min-h-0 !w-11 !p-0"
            disabled={submitting}
            aria-disabled={!valid && !submitting ? 'true' : undefined}
            aria-label={submitting ? 'Starting research' : 'Start research'}
            title="Start research (Ctrl / ⌘ + Enter)"
          >
            {submitting ? <Loader2 className="h-5 w-5 animate-spin" aria-hidden="true" /> : <ArrowUp className="h-5 w-5" aria-hidden="true" />}
          </button>
        </div>

        {error && <div className="px-4 pb-4"><ErrorBanner title="Couldn’t start the research" error={error} /></div>}
      </form>

      <p aria-live="polite" className="mt-3 text-center text-sm text-fg-subtle">
        <span className="font-semibold text-fg-muted">{m.label}:</span> {m.blurb} · {m.eta}
      </p>

      <section aria-labelledby="suggest-title" className="animate-fade-up mt-9 w-full">
        <h2 id="suggest-title" className="sr-only">Suggested topics</h2>
        <ul className="grid gap-3 sm:grid-cols-3">
          {SUGGESTION_CARDS.map((c) => {
            const Icon = CARD_ICONS[c.icon]
            return (
              <li key={c.title}>
                <button
                  type="button"
                  onClick={() => pickSuggestion(c.topic)}
                  className="glass-soft flex h-full w-full cursor-pointer flex-col gap-3 p-4 text-left transition-[transform,border-color,background-color] hover:-translate-y-0.5 hover:border-accent/40 hover:bg-white/[0.08]"
                >
                  <span className="flex items-center justify-between">
                    <span className="grid h-10 w-10 place-items-center rounded-xl bg-white/[0.07] text-accent-hi">
                      <Icon className="h-5 w-5" aria-hidden="true" />
                    </span>
                    <span className="chip">{c.tag}</span>
                  </span>
                  <span>
                    <span className="block text-[0.98rem] font-semibold text-fg">{c.title}</span>
                    <span className="mt-1 block text-sm leading-snug text-fg-muted">{c.desc}</span>
                  </span>
                </button>
              </li>
            )
          })}
        </ul>
      </section>
    </div>
  )
}
