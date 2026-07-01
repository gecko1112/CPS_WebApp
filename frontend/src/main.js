import { createApp } from 'vue'
import PrimeVue from 'primevue/config'
import Aura from '@primevue/themes/aura'
import VueApexCharts from 'vue3-apexcharts'

import App from './App.vue'
import router from './router'
import './style.css'

const app = createApp(App)

app.use(router)

app.use(PrimeVue, {
  theme: {
    preset: Aura,
    options: {
      darkModeSelector: '.dark',
    },
  },
})

app.use(VueApexCharts)

app.mount('#app')

// Register the notification service worker (best-effort; enables OS-level
// notifications on mobile). Silently ignored where unsupported / not secure.
if ('serviceWorker' in navigator) {
  window.addEventListener('load', () => {
    navigator.serviceWorker.register('/sw.js').catch(() => {})
  })
}
