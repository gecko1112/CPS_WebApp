// Best-effort OS-level notifications (a "push" while the tab is backgrounded).
//
// Caveats (surfaced to the user in Settings):
//   - Needs a secure context: works on localhost, and over HTTPS. Plain HTTP on
//     the LAN (the Pi) blocks the Notification API.
//   - Android Chrome requires ServiceWorkerRegistration.showNotification(); the
//     bare `new Notification()` throws there - so we prefer the service worker.
//   - iOS Safari only allows this once the site is installed to the home screen
//     (PWA). Until then it reports unsupported.
//   - True push with the browser fully closed needs the Push API + a push
//     server - out of scope; this covers backgrounded-tab notifications.
import { ref } from 'vue'

export const notificationsSupported =
  typeof window !== 'undefined' && 'Notification' in window

export const notificationPermission = ref(
  notificationsSupported ? Notification.permission : 'unsupported',
)

export async function enableNotifications() {
  if (!notificationsSupported) return 'unsupported'
  try {
    const p = await Notification.requestPermission()
    notificationPermission.value = p
    return p
  } catch {
    return 'denied'
  }
}

export async function notify(title, body, tag) {
  if (!notificationsSupported || Notification.permission !== 'granted') return
  try {
    // Prefer the service worker (required on Android); fall back to the ctor.
    if ('serviceWorker' in navigator) {
      const reg = await navigator.serviceWorker.getRegistration()
      if (reg) {
        reg.showNotification(title, { body, tag })
        return
      }
    }
    new Notification(title, { body, tag })
  } catch {
    /* best-effort - never let a notification failure break the app */
  }
}
