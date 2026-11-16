import { useEffect, useRef, useState } from 'react'
import { cx } from '../utils'

// Order matches the report. Each id maps to a <section id="sec-{id}"> rendered by <Section>.
export const REPORT_SECTIONS = [
  { id: 'summary', label: 'Summary' },
  { id: 'objective', label: 'Objective' },
  { id: 'findings', label: 'Key findings' },
  { id: 'analysis', label: 'Analysis' },
  { id: 'comparison', label: 'Comparison' },
  { id: 'conflicts', label: 'Conflicts' },
  { id: 'limitations', label: 'Limitations' },
  { id: 'conclusion', label: 'Conclusion' },
  { id: 'sources', label: 'References' },
  { id: 'followup', label: 'Follow-up' },
]

/**
 * Tracks which section the reader is in: the last section whose top has passed a reading line ~1/3 down the viewport
 * (the first section when nothing has). Computed from positions, so it is also right at the very top and bottom.
 */
export function useScrollSpy(ids) {
  const [active, setActive] = useState(ids[0])
  const key = ids.join('|')
  useEffect(() => {
    const els = ids.map((i) => document.getElementById(`sec-${i}`)).filter(Boolean)
    if (!els.length) return
    const compute = () => {
      const line = window.innerHeight * 0.32
      let cur = els[0]
      for (const el of els) {
        if (el.getBoundingClientRect().top <= line) cur = el
        else break
      }
      setActive(cur.id.replace('sec-', ''))
    }
    // Recompute on scroll (rAF-throttled) and whenever the page's height changes (fonts, images, late content),
    // so the highlight is right immediately after load as well as while scrolling.
    let raf = 0
    const schedule = () => { if (!raf) raf = requestAnimationFrame(() => { raf = 0; compute() }) }
    compute()
    window.addEventListener('scroll', schedule, { passive: true })
    window.addEventListener('resize', schedule)
    const ro = 'ResizeObserver' in window ? new ResizeObserver(schedule) : null
    ro?.observe(document.body)
    return () => {
      cancelAnimationFrame(raf)
      ro?.disconnect()
      window.removeEventListener('scroll', schedule)
      window.removeEventListener('resize', schedule)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return [active, setActive]
}

/**
 * Section navigation for long reports.
 *  variant="rail": vertical "On this page" list, shown beside the report on wide screens.
 *  variant="bar" : sticky horizontally-scrolling pills, shown on narrower screens.
 */
export default function SectionNav({ variant, active, onJump }) {
  const barRef = useRef(null)

  // Keep the active pill visible inside the horizontal bar.
  useEffect(() => {
    if (variant !== 'bar' || !barRef.current) return
    const bar = barRef.current
    const el = bar.querySelector('[aria-current="true"]')
    if (el && bar.offsetParent !== null) {
      bar.scrollTo({ left: el.offsetLeft - bar.clientWidth / 2 + el.clientWidth / 2, behavior: 'auto' })
    }
  }, [active, variant])

  if (variant === 'rail') {
    return (
      <nav aria-label="Report sections" className="hidden min-[1360px]:block">
        <div className="sticky top-8">
          <p className="mb-3 font-sans text-[0.68rem] font-bold uppercase tracking-[0.14em] text-fg-subtle">On this page</p>
          <ol className="flex flex-col">
            {REPORT_SECTIONS.map((s) => (
              <li key={s.id}>
                <button
                  type="button"
                  onClick={() => onJump(s.id)}
                  aria-current={active === s.id ? 'true' : undefined}
                  className={cx(
                    'w-full cursor-pointer border-l-2 py-1.5 pl-3.5 text-left text-[0.9rem] transition-colors',
                    active === s.id ? 'border-accent font-bold text-fg' : 'border-line text-fg-muted hover:border-line-strong hover:text-fg',
                  )}
                >
                  {s.label}
                </button>
              </li>
            ))}
          </ol>
        </div>
      </nav>
    )
  }

  return (
    <nav
      aria-label="Report sections"
      className="sticky top-[4.1rem] z-20 border-b border-line bg-[rgb(14_10_26/0.95)] min-[1360px]:hidden lg:top-4"
    >
      <ol ref={barRef} className="flex gap-1.5 overflow-x-auto py-2 [scrollbar-width:none]">
        {REPORT_SECTIONS.map((s) => (
          <li key={s.id} className="shrink-0">
            <button
              type="button"
              onClick={() => onJump(s.id)}
              aria-current={active === s.id ? 'true' : undefined}
              className={cx(
                'min-h-9 cursor-pointer whitespace-nowrap rounded-full border px-3.5 text-[0.82rem] font-bold transition-colors',
                active === s.id
                  ? 'border-accent/50 bg-accent/10 text-accent-hi'
                  : 'border-transparent text-fg-muted hover:bg-fg/5 hover:text-fg',
              )}
            >
              {s.label}
            </button>
          </li>
        ))}
      </ol>
    </nav>
  )
}
