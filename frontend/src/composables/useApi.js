// Centralised API client. All backend calls go through here so changes
// (auth headers, base URL, error handling) happen in ONE place.

import { ref } from 'vue'

const TOKEN_KEY = 'plantcps_token'
const ROLE_KEY = 'plantcps_role'

// Reactive auth state — components can watch this
export const authState = ref({
  token: localStorage.getItem(TOKEN_KEY),
  role: localStorage.getItem(ROLE_KEY),
})

function authHeaders() {
  return authState.value.token
    ? { Authorization: `Bearer ${authState.value.token}` }
    : {}
}

async function request(path, options = {}) {
  const res = await fetch(path, {
    ...options,
    headers: {
      'Content-Type': 'application/json',
      ...authHeaders(),
      ...(options.headers || {}),
    },
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(`${res.status}: ${detail}`)
  }
  return res.json()
}

export async function login(username, password) {
  // FastAPI's OAuth2PasswordRequestForm expects form-encoded, NOT JSON
  const body = new URLSearchParams({ username, password })
  const res = await fetch('/api/auth/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) throw new Error('Invalid credentials')
  const data = await res.json()
  authState.value = { token: data.access_token, role: data.role }
  localStorage.setItem(TOKEN_KEY, data.access_token)
  localStorage.setItem(ROLE_KEY, data.role)
  return data
}

export function logout() {
  authState.value = { token: null, role: null }
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

export const api = {
  latest: () => request('/api/sensors/latest'),
  history: (sensor, maxPoints = 200) =>
    request(`/api/sensors/history?sensor=${sensor}&max_points=${maxPoints}`),
  status: () => request('/api/system/status'),
  alertsActive: () => request('/api/alerts/active'),
  alertsRecent: (limit = 20) => request(`/api/alerts/recent?limit=${limit}`),
  water: (durationS = 30) =>
    request('/api/commands/water', {
      method: 'POST',
      body: JSON.stringify({ confirm: true, duration_s: durationS }),
    }),

  // ── MQTT INTEGRATION POINT ──────────────────────────────────────────────
  // These endpoints are already wired — no frontend changes needed when
  // the backend swaps the fake alert loop for real MQTT messages.
  // ────────────────────────────────────────────────────────────────────────
  alerts: {
    active: () => request('/api/alerts/active'),
    recent: (limit = 20) => request(`/api/alerts/recent?limit=${limit}`),
  },
}
