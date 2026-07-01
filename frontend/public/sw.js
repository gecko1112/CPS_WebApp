// Minimal service worker — its only job is to enable OS-level notifications
// (Android Chrome requires ServiceWorkerRegistration.showNotification) and to
// focus the app when a notification is tapped. No offline caching.
self.addEventListener('install', () => self.skipWaiting())
self.addEventListener('activate', (event) => event.waitUntil(self.clients.claim()))

self.addEventListener('notificationclick', (event) => {
  event.notification.close()
  event.waitUntil(
    self.clients.matchAll({ type: 'window', includeUncontrolled: true }).then((clients) => {
      for (const client of clients) {
        if ('focus' in client) return client.focus()
      }
      if (self.clients.openWindow) return self.clients.openWindow('/dashboard')
    }),
  )
})
