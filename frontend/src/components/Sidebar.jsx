import { useEffect, useRef } from 'react'
import { AlertTriangle, Bookmark, CheckCircle2, History, Loader2, Menu, Plus, Settings, ShieldCheck, X } from 'lucide-react'
import { cx } from '../utils'
import LogoMark from './LogoMark'

function Logo() {
  return (
    <a href="#/" className="flex items-center gap-3 rounded-lg" aria-label="Webwise AI home">
      <LogoMark className="h-9 w-9 shrink-0" />
      <span className="font-serif text-[1.4rem] font-semibold leading-none tracking-tight text-fg">
        Webwise <span className="italic text-accent-hi">AI</span>
      </span>
    </a>
  )
}

function NavLink({ href, icon: Icon, label, active, onClick }) {
  return (
    <a
      href={href}
      onClick={onClick}
      aria-current={active ? 'page' : undefined}
      className={cx(
        'flex min-h-11 items-center gap-3 rounded-xl px-3 text-[0.95rem] transition-colors',
        active ? 'bg-white/[0.09] font-semibold text-fg' : 'text-fg-muted hover:bg-white/[0.05] hover:text-fg',
      )}
    >
      <Icon className="h-[1.1rem] w-[1.1rem] shrink-0" aria-hidden="true" />
      {label}
    </a>
  )
}

function StatusIcon({ status }) {
  if (status === 'completed') return <CheckCircle2 className="h-3.5 w-3.5 shrink-0 text-ok" aria-label="Completed" />
  if (status === 'failed') return <AlertTriangle className="h-3.5 w-3.5 shrink-0 text-warn" aria-label="Failed" />
  return <Loader2 className="h-3.5 w-3.5 shrink-0 animate-spin text-accent-hi" aria-label="In progress" />
}

// Section labels are quiet sentence-case text, not shouty uppercase.
const LABEL = 'px-3 font-sans text-[0.8rem] font-medium tracking-normal text-fg-subtle'

export default function Sidebar({ route, recent, open, onOpen, onClose }) {
  const closeRef = useRef(null)
  const name = route.name

  // Esc closes the mobile drawer; focus moves into it when it opens.
  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e) => e.key === 'Escape' && onClose()
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [open, onClose])

  return (
    <>
      {/* Mobile top bar */}
      <header className="sticky top-0 z-30 flex items-center justify-between border-b border-line bg-[rgb(12_8_24/0.94)] px-4 py-2.5 lg:hidden">
        <Logo />
        <button
          type="button"
          onClick={onOpen}
          className="btn btn-ghost !min-h-11 !w-11 !px-0"
          aria-label="Open menu"
          aria-expanded={open}
          aria-controls="app-sidebar"
        >
          <Menu className="h-5 w-5" aria-hidden="true" />
        </button>
      </header>

      {open && <div className="fixed inset-0 z-40 bg-black/65 lg:hidden" onClick={onClose} aria-hidden="true" />}

      <aside
        id="app-sidebar"
        className={cx(
          'fixed inset-y-0 left-0 z-50 flex w-72 flex-col gap-5 border-r border-line bg-[rgb(12_8_24/0.97)] p-4 transition-transform duration-200',
          'lg:sticky lg:top-4 lg:z-20 lg:h-[calc(100vh-2rem)] lg:translate-x-0 lg:self-start lg:bg-black/25',
          open ? 'translate-x-0' : '-translate-x-full',
        )}
        aria-label="Sidebar"
      >
        <div className="flex items-center justify-between px-1">
          <Logo />
          <button ref={closeRef} type="button" onClick={onClose} className="btn btn-ghost !min-h-10 !w-10 !px-0 lg:hidden" aria-label="Close menu">
            <X className="h-5 w-5" aria-hidden="true" />
          </button>
        </div>

        <a
          href="#/"
          onClick={onClose}
          className="flex min-h-11 items-center gap-3 rounded-xl border border-line-strong bg-white/[0.08] px-3 text-[0.95rem] font-semibold text-fg transition-colors hover:bg-white/[0.13]"
        >
          <Plus className="h-[1.1rem] w-[1.1rem]" aria-hidden="true" /> New Research
        </a>

        <nav aria-label="Main" className="flex flex-col gap-1">
          <p className={cx(LABEL, 'mb-1')}>Workspace</p>
          <NavLink href="#/history" icon={History} label="Research History" active={name === 'history'} onClick={onClose} />
          <NavLink href="#/saved" icon={Bookmark} label="Saved Reports" active={name === 'saved'} onClick={onClose} />
          <NavLink href="#/settings" icon={Settings} label="Settings" active={name === 'settings'} onClick={onClose} />
        </nav>

        <div className="min-h-0 flex-1 overflow-y-auto">
          <h2 className={cx(LABEL, 'mb-2')}>Recent</h2>
          {recent.length === 0 ? (
            <p className="px-3 text-sm text-fg-subtle">Your research will appear here.</p>
          ) : (
            <ul className="flex flex-col gap-0.5">
              {recent.map((r) => (
                <li key={r.id}>
                  <a
                    href={`#/research/${r.id}`}
                    onClick={onClose}
                    aria-current={route.name === 'research' && route.id === r.id ? 'page' : undefined}
                    className={cx(
                      'flex min-h-10 items-center gap-2.5 rounded-lg px-3 py-1.5 text-sm transition-colors',
                      route.name === 'research' && route.id === r.id ? 'bg-white/[0.09] text-fg' : 'text-fg-muted hover:bg-white/[0.05]',
                    )}
                  >
                    <StatusIcon status={r.status} />
                    <span className="line-clamp-2 leading-snug">{r.title || r.topic}</span>
                  </a>
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="rounded-2xl border border-line bg-white/[0.04] p-4 text-center">
          <ShieldCheck className="mx-auto h-5 w-5 text-accent-hi" aria-hidden="true" />
          <p className="mt-2 text-sm font-semibold text-fg">Evidence first</p>
          <p className="mt-1 text-xs leading-relaxed text-fg-muted">
            Webwise AI only cites sources it actually retrieved. AI can still be wrong, so check the citations.
          </p>
        </div>
      </aside>
    </>
  )
}
