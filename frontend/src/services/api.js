// Every call goes to the FastAPI backend. API keys live ONLY on the server; nothing secret is here.
const BASE = import.meta.env.VITE_API_BASE ?? ''

export class ApiError extends Error {
  constructor(code, message, { retryable = false, status = 0 } = {}) {
    super(message)
    this.name = 'ApiError'
    this.code = code
    this.retryable = retryable
    this.status = status
  }
}

// Anonymous, random per-browser id. The server uses it only to scope the history list so visitors can't see each
// other's research. It is NOT a credential.
const CLIENT_KEY = 'webwise.clientId'
let memoryId = null
function newId() {
  if (crypto.randomUUID) return crypto.randomUUID().replace(/-/g, '')
  const a = new Uint8Array(16)
  crypto.getRandomValues(a)
  return [...a].map((b) => b.toString(16).padStart(2, '0')).join('')
}
function clientId() {
  try {
    let v = localStorage.getItem(CLIENT_KEY)
    if (!v || !/^[A-Za-z0-9_-]{16,64}$/.test(v)) {
      v = newId()
      localStorage.setItem(CLIENT_KEY, v)
    }
    return v
  } catch {
    return (memoryId ??= newId()) // storage blocked: fall back to a per-tab id
  }
}

async function request(path, { method = 'GET', body, signal } = {}) {
  let res
  try {
    res = await fetch(BASE + path, {
      method,
      headers: { 'X-Client-Id': clientId(), ...(body ? { 'Content-Type': 'application/json' } : {}) },
      body: body ? JSON.stringify(body) : undefined,
      signal,
    })
  } catch (e) {
    if (e?.name === 'AbortError') throw e
    throw new ApiError('NETWORK', 'Cannot reach the backend. Make sure it is running (uvicorn on port 8000).', { retryable: true })
  }

  if (res.status === 204) return null
  const isJson = (res.headers.get('content-type') || '').includes('json')

  if (!res.ok) {
    const payload = isJson ? await res.json().catch(() => null) : null
    const err = payload?.error
    if (err) throw new ApiError(err.code, err.message, { retryable: !!err.retryable, status: res.status })
    if (res.status >= 500) {
      throw new ApiError('BACKEND_DOWN', 'The backend is not responding. Make sure it is running (uvicorn on port 8000).', { retryable: true, status: res.status })
    }
    throw new ApiError(`HTTP_${res.status}`, `Request failed (${res.status}).`, { status: res.status })
  }
  return isJson ? res.json() : res
}

export const api = {
  health: (signal) => request('/api/health', { signal }),
  startResearch: (topic, mode) => request('/api/research', { method: 'POST', body: { topic, mode } }),
  getResearch: (id, signal) => request(`/api/research/${id}`, { signal }),
  retry: (id) => request(`/api/research/${id}/retry`, { method: 'POST' }),
  setSaved: (id, saved) => request(`/api/research/${id}/saved`, { method: 'PATCH', body: { saved } }),
  remove: (id) => request(`/api/research/${id}`, { method: 'DELETE' }),
  history: ({ saved = false, limit = 50 } = {}, signal) => request(`/api/history?saved=${saved}&limit=${limit}`, { signal }),
  followUp: (id, question) => request(`/api/research/${id}/follow-up`, { method: 'POST', body: { question } }),

  /** Downloads the PDF through fetch so a failure shows a message instead of navigating away. */
  async downloadPdf(id) {
    const res = await request(`/api/research/${id}/pdf`)
    const blob = await res.blob()
    const cd = res.headers.get('content-disposition') || ''
    const name = /filename="?([^";]+)"?/.exec(cd)?.[1] || 'webwise-report.pdf'
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = name
    document.body.appendChild(a)
    a.click()
    a.remove()
    setTimeout(() => URL.revokeObjectURL(url), 2000)
    return name
  },
}
