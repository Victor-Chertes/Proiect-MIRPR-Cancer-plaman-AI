// Thin client for the Flask backend. In development Vite proxies /api to it.
const API_BASE = import.meta.env.VITE_API_URL ?? ''

export async function predict(file) {
  const body = new FormData()
  body.append('image', file)

  const res = await fetch(`${API_BASE}/api/predict`, { method: 'POST', body })
  const data = await res.json().catch(() => ({}))
  if (!res.ok) {
    throw new Error(data.error ?? `Server responded with ${res.status}`)
  }
  return data
}

export async function health() {
  const res = await fetch(`${API_BASE}/api/health`)
  if (!res.ok) throw new Error('Backend unavailable')
  return res.json()
}
