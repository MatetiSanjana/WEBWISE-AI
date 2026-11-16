import { CheckCircle2, RefreshCw, RotateCcw, XCircle } from 'lucide-react'
import { useSettings } from '../hooks/useSettings'
import { useHealth } from '../hooks/useMisc'
import { MODES } from '../constants'
import { cx } from '../utils'

function Radio({ name, value, current, onChange, label, hint }) {
  const active = current === value
  return (
    <label className={cx(
      'flex cursor-pointer items-start gap-3 rounded-xl border p-3.5 transition-colors has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-cyan-300',
      active ? 'border-accent/60 bg-accent/10' : 'border-line bg-fg/[0.04] hover:bg-fg/[0.07]',
    )}>
      <input type="radio" name={name} value={value} checked={active} onChange={() => onChange(value)} className="mt-1 h-4 w-4 accent-accent" />
      <span>
        <span className="block text-sm font-semibold text-fg">{label}</span>
        {hint && <span className="block text-[0.8rem] text-fg-muted">{hint}</span>}
      </span>
    </label>
  )
}

function Row({ ok, label, detail }) {
  return (
    <li className="flex items-center gap-2.5 text-sm">
      {ok ? <CheckCircle2 className="h-4 w-4 text-ok" aria-label="OK" /> : <XCircle className="h-4 w-4 text-bad" aria-label="Not configured" />}
      <span className="text-fg">{label}</span>
      {detail && <span className="text-fg-subtle">{detail}</span>}
    </li>
  )
}

export default function SettingsPage() {
  const { settings, update, reset } = useSettings()
  const { health, error, loading, refresh } = useHealth()

  return (
    <div className="mx-auto flex max-w-2xl flex-col gap-5 pt-4">
      <h1 className="text-2xl font-bold text-fg sm:text-3xl">Settings</h1>

      <section className="glass p-5" aria-labelledby="s-mode">
        <h2 id="s-mode" className="text-lg font-bold text-fg">Default research mode</h2>
        <p className="mb-3 text-sm text-fg-muted">Used when you open a new research. You can still change it each time.</p>
        <div className="grid gap-3 sm:grid-cols-2" role="radiogroup" aria-labelledby="s-mode">
          {Object.values(MODES).map((m) => (
            <Radio key={m.id} name="default-mode" value={m.id} current={settings.defaultMode} onChange={(v) => update({ defaultMode: v })} label={m.label} hint={m.blurb} />
          ))}
        </div>
      </section>

      <section className="glass p-5" aria-labelledby="s-bg">
        <h2 id="s-bg" className="text-lg font-bold text-fg">Animated background</h2>
        <p className="mb-3 text-sm text-fg-muted">A slowly drifting star field and nebula. Turn it off if it slows your computer or you prefer a calmer screen.</p>
        <div className="grid gap-3" role="radiogroup" aria-labelledby="s-bg">
          <Radio name="bg" value="auto" current={settings.background} onChange={(v) => update({ background: v })} label="Automatic" hint="Animated, but a still image if your system asks for reduced motion." />
          <Radio name="bg" value="on" current={settings.background} onChange={(v) => update({ background: v })} label="Always animated" />
          <Radio name="bg" value="off" current={settings.background} onChange={(v) => update({ background: v })} label="Off (plain gradient)" hint="Best for performance and accessibility." />
        </div>
      </section>

      <section className="glass p-5" aria-labelledby="s-health">
        <div className="flex items-center justify-between gap-3">
          <h2 id="s-health" className="text-lg font-bold text-fg">Server status</h2>
          <button type="button" className="btn btn-ghost !min-h-10" onClick={refresh} disabled={loading}>
            <RefreshCw className={cx('h-4 w-4', loading && 'animate-spin')} aria-hidden="true" /> Refresh
          </button>
        </div>
        {error ? (
          <p role="alert" className="mt-3 text-sm text-fg-muted">{error.message}</p>
        ) : health ? (
          <ul className="mt-3 flex flex-col gap-2">
            <Row ok label="Backend reachable" />
            <Row ok={health.tavily_configured} label="Tavily web search key" detail={health.tavily_configured ? 'configured' : 'missing — set TAVILY_API_KEY'} />
            <Row ok={health.gemini_configured} label="Gemini key" detail={health.gemini_configured ? `configured · model ${health.gemini_model}` : 'missing — set GEMINI_API_KEY'} />
          </ul>
        ) : <p className="mt-3 text-sm text-fg-muted">Checking…</p>}
        <p className="mt-4 text-xs text-fg-subtle">API keys are stored only on the server in the <code className="rounded bg-black/30 px-1">.env</code> file. They are never sent to this browser.</p>
      </section>

      <div>
        <button type="button" className="btn btn-ghost" onClick={reset}><RotateCcw className="h-4 w-4" aria-hidden="true" /> Reset settings</button>
      </div>
    </div>
  )
}
