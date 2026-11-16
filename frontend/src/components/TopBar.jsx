import { Settings2 } from 'lucide-react'
import { useHealth } from '../hooks/useMisc'
import { cx } from '../utils'

/** Slim desktop header: live backend/model status on the left, a shortcut to Settings on the right. */
export default function TopBar() {
  const { health, error } = useHealth()
  let dot = 'bg-fg-subtle'
  let label = 'Checking…'
  if (error) { dot = 'bg-bad'; label = 'Backend offline' }
  else if (health) {
    if (health.status === 'ok') { dot = 'bg-ok'; label = health.gemini_model } else { dot = 'bg-warn'; label = 'Setup needed' }
  }
  return (
    <div className="hidden items-center justify-between px-8 pt-5 lg:flex">
      <span
        className="inline-flex items-center gap-2.5 rounded-full border border-line-strong bg-white/[0.04] px-4 py-2 text-sm text-fg-muted"
        title="The AI model that writes reports, and whether the backend is reachable"
      >
        <span className={cx('h-2 w-2 rounded-full', dot)} aria-hidden="true" />
        <span className="sr-only">Status: </span>
        {label}
      </span>
      <a href="#/settings" className="btn btn-ghost !min-h-10 !px-4">
        <Settings2 className="h-4 w-4" aria-hidden="true" /> Settings
      </a>
    </div>
  )
}
