/** Only http(s) URLs may become links (blocks javascript: and other schemes from untrusted data). */
export function safeHref(url) {
  try {
    const u = new URL(url)
    return u.protocol === 'http:' || u.protocol === 'https:' ? u.href : undefined
  } catch {
    return undefined
  }
}

export function formatDate(iso, withTime = true) {
  if (!iso) return ''
  const d = new Date(iso)
  if (Number.isNaN(d.getTime())) return ''
  return new Intl.DateTimeFormat(
    undefined,
    withTime ? { dateStyle: 'medium', timeStyle: 'short' } : { dateStyle: 'medium' },
  ).format(d)
}

export function formatElapsed(seconds) {
  const s = Math.max(0, Math.floor(seconds))
  return `${Math.floor(s / 60)}:${String(s % 60).padStart(2, '0')}`
}

export const cx = (...parts) => parts.filter(Boolean).join(' ')

/** Short, readable URL for cards: host + path, one line, ellipsised. The full URL stays in the link and tooltip. */
export function displayUrl(url, max = 58) {
  try {
    const u = new URL(url)
    const text = u.hostname.replace(/^www\./, '') + (u.pathname === '/' ? '' : u.pathname) + u.search
    return text.length > max ? text.slice(0, max - 1) + '…' : text
  } catch {
    return url
  }
}
