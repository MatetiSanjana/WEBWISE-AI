import { Telescope, Zap } from 'lucide-react'
import { MODES } from '../constants'
import { cx } from '../utils'

const ICONS = { quick: Zap, deep: Telescope }
const SHORT = { quick: 'Quick', deep: 'Deep' }

/** Compact segmented control (native radios, restyled) that lives inside the composer. Arrow keys work natively. */
export default function ModeSelector({ value, onChange, disabled }) {
  return (
    <fieldset className="inline-flex rounded-full border border-line-strong bg-black/25 p-1" disabled={disabled}>
      <legend className="sr-only">Research mode</legend>
      {Object.values(MODES).map((m) => {
        const Icon = ICONS[m.id]
        const active = value === m.id
        return (
          <label
            key={m.id}
            title={`${m.label}: ${m.blurb}`}
            className={cx(
              'relative flex min-h-9 cursor-pointer items-center gap-1.5 rounded-full px-3.5 text-sm font-semibold transition-colors',
              'has-[:focus-visible]:outline-2 has-[:focus-visible]:outline-offset-1 has-[:focus-visible]:outline-accent-hi',
              active ? 'bg-accent/20 text-accent-hi' : 'text-fg-muted hover:text-fg',
              disabled && 'cursor-not-allowed opacity-60',
            )}
          >
            <input type="radio" name="research-mode" value={m.id} checked={active} onChange={() => onChange(m.id)} className="sr-only" />
            <Icon className="h-4 w-4" aria-hidden="true" />
            <span>{SHORT[m.id]}</span>
            <span className="sr-only"> research, {m.blurb}</span>
          </label>
        )
      })}
    </fieldset>
  )
}
