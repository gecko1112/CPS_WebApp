// Diffs the active-alerts list each poll and fires an in-app toast (plus an
// OS notification when the tab is backgrounded) for each genuinely NEW alert.
import { pushToast } from './useToasts'
import { notify } from './useNotifications'

const seen = new Set()
let initialized = false

function keyOf(a) {
  return `${a.timestamp || ''}|${a.component || ''}|${a.description || ''}`
}

export function watchAlerts(alerts) {
  const list = alerts || []

  // First load: treat existing alerts as already-seen so opening the app
  // doesn't spam a toast for every pre-existing alert.
  if (!initialized) {
    list.forEach((a) => seen.add(keyOf(a)))
    initialized = true
    return
  }

  for (const a of list) {
    const k = keyOf(a)
    if (seen.has(k)) continue
    seen.add(k)

    const critical = a.severity === 'critical'
    const title = critical ? 'Critical alert' : 'Plant alert'
    pushToast({
      severity: critical ? 'critical' : 'warning',
      title,
      message: a.description,
    })
    // Push-like notification when the user isn't looking at the page.
    if (typeof document !== 'undefined' && document.visibilityState === 'hidden') {
      notify(title, a.description || 'A new alert was raised.', k)
    }
  }

  // Keep the seen-set bounded.
  if (seen.size > 300) {
    seen.clear()
    list.forEach((a) => seen.add(keyOf(a)))
  }
}

export function resetAlertWatcher() {
  seen.clear()
  initialized = false
}
