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
    // FastAPI returns {"detail": "..."} — surface that as a clean message.
    let detail = await res.text()
    try {
      const parsed = JSON.parse(detail)
      if (parsed?.detail) {
        detail =
          typeof parsed.detail === 'string'
            ? parsed.detail
            : JSON.stringify(parsed.detail)
      }
    } catch {
      /* response body was not JSON — keep the raw text */
    }
    const err = new Error(detail || `Request failed (${res.status})`)
    err.status = res.status
    throw err
  }
  return res.json()
}

export async function login(email, password) {
  // fastapi-users uses OAuth2 conventions: the form field is called "username"
  // even though we send an email. Login URL is /api/auth/jwt/login.
  const body = new URLSearchParams({ username: email, password })
  const res = await fetch('/api/auth/jwt/login', {
    method: 'POST',
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
    body,
  })
  if (!res.ok) throw new Error('Invalid credentials')
  const { access_token } = await res.json()

  // Token in hand — now fetch /me to discover the role.
  authState.value = { token: access_token, role: null }
  const me = await fetch('/api/users/me', {
    headers: { Authorization: `Bearer ${access_token}` },
  }).then((r) => r.json())

  authState.value = { token: access_token, role: me.role, email: me.email }
  localStorage.setItem(TOKEN_KEY, access_token)
  localStorage.setItem(ROLE_KEY, me.role)
  return { access_token, role: me.role, email: me.email }
}

export async function register(email, password) {
  const res = await fetch('/api/auth/register', {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const detail = await res.text()
    throw new Error(detail || 'Registration failed')
  }
  return res.json()
}

export function logout() {
  authState.value = { token: null, role: null }
  localStorage.removeItem(TOKEN_KEY)
  localStorage.removeItem(ROLE_KEY)
}

export const api = {
  latest: () => request('/api/sensors/latest'),
  history: (sensor, maxPoints = 200, hours = 24) =>
    request(
      `/api/sensors/history?sensor=${sensor}&max_points=${maxPoints}&hours=${hours}`,
    ),
  status: () => request('/api/system/status'),
  components: () => request('/api/system/components'),
  alertsActive: () => request('/api/alerts/active'),
  alertsRecent: (limit = 20) => request(`/api/alerts/recent?limit=${limit}`),
  water: (durationS = 30, action = 'start') =>
    request('/api/commands/water', {
      method: 'POST',
      body: JSON.stringify({ confirm: true, action, duration_s: durationS }),
    }),
  wateringHistory: (limit = 20) =>
    request(`/api/watering/history?limit=${limit}`),
  notifyTest: () => request('/api/notify/test', { method: 'POST' }),
  wateringConfig: () => request('/api/config/watering'),
  updateWateringConfig: (payload) =>
    request('/api/config/watering', {
      method: 'PATCH',
      body: JSON.stringify(payload),
    }),
}
