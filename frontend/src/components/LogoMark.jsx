/**
 * Webwise AI mark: a "W" with a small superscript dot (the same dot that appears as a citation marker in reports),
 * on a violet orb. Pure SVG (no font dependency) so it matches public/favicon.svg exactly.
 */
import { useId } from 'react'

export default function LogoMark({ className = 'h-9 w-9' }) {
  const gid = useId().replace(/:/g, '')
  return (
    <svg viewBox="0 0 32 32" className={className} aria-hidden="true">
      <defs>
        <linearGradient id={gid} x1="6" y1="3" x2="26" y2="30" gradientUnits="userSpaceOnUse">
          <stop offset="0" stopColor="#c6b2ff" />
          <stop offset="1" stopColor="#7c4dff" />
        </linearGradient>
      </defs>
      <circle cx="16" cy="16" r="16" fill={`url(#${gid})`} />
      <path
        d="M7.6 12 11.2 22.4l4.4-8 4.4 8 3.6-10.4"
        fill="none"
        stroke="#ffffff"
        strokeWidth="2.5"
        strokeLinecap="round"
        strokeLinejoin="round"
      />
      <circle cx="24.4" cy="8.2" r="1.9" fill="#ffffff" />
    </svg>
  )
}
