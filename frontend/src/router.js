import { createRouter, createWebHistory } from 'vue-router'
import { authState } from './composables/useApi'

import LoginScreen from './components/LoginScreen.vue'
import WelcomePage from './components/WelcomePage.vue'
import Dashboard from './components/Dashboard.vue'
import SettingsPage from './components/SettingsPage.vue'

const routes = [
  { path: '/login', name: 'login', component: LoginScreen, meta: { guest: true } },
  { path: '/', name: 'welcome', component: WelcomePage },
  { path: '/dashboard', name: 'dashboard', component: Dashboard },
  { path: '/settings', name: 'settings', component: SettingsPage },
]

const router = createRouter({
  history: createWebHistory(),
  routes,
})

router.beforeEach((to) => {
  const isAuthenticated = Boolean(authState.value.token)

  if (!to.meta.guest && !isAuthenticated) {
    return { name: 'login' }
  }

  if (to.name === 'login' && isAuthenticated) {
    const preferred = localStorage.getItem('plantcps_landing') || 'welcome'
    return { name: preferred }
  }
})

export default router
