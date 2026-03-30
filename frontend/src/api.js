const API_BASE = import.meta.env.VITE_API_URL || 'http://localhost:8000'

async function request(url, options = {}) {
  const res = await fetch(`${API_BASE}${url}`, options)
  if (!res.ok) {
    const err = await res.json().catch(() => ({ detail: res.statusText }))
    throw new Error(err.detail || 'Request failed')
  }
  return res.json()
}

export const api = {
  getUsers: (params = {}) =>
    request(`/api/users?${new URLSearchParams(params)}`),

  getUser: (id) =>
    request(`/api/users/${id}`),

  cancelUser: (id) =>
    request(`/api/users/${id}/cancel`, { method: 'POST' }),

  respondIntervention: (id, outcome) =>
    request(`/api/interventions/${id}/respond`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ outcome }),
    }),

  getAnalytics: (vertical) => {
    const params = vertical ? `?vertical=${vertical}` : ''
    return request(`/api/analytics${params}`)
  },

  getVerticals: () =>
    request('/api/verticals'),

  resetDemo: (vertical) => {
    const params = vertical ? `?vertical=${vertical}` : ''
    return request(`/api/seed${params}`, { method: 'POST' })
  },

  ingestEvent: (event) =>
    request('/api/events', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify(event),
    }),
}
