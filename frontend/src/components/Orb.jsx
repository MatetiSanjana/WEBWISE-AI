import { cx } from '../utils'

/** Decorative glass planet. `pulse` makes it breathe while research is running. Purely visual (aria-hidden). */
export default function Orb({ size = '5.25rem', pulse = false, className }) {
  return <div aria-hidden="true" className={cx('orb shrink-0', pulse && 'orb-pulse', className)} style={{ '--orb': size }} />
}
