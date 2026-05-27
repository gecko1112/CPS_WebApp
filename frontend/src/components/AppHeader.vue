<script setup>
import { computed } from 'vue'
import { RouterLink, useRoute } from 'vue-router'
import Button from 'primevue/button'
import { Sprout, LogOut, LayoutDashboard, Settings } from 'lucide-vue-next'

import { authState, logout } from '../composables/useApi'
import router from '../router'

const route = useRoute()
const isLoggedIn = computed(() => Boolean(authState.value.token))

defineProps({
  transparent: { type: Boolean, default: false },
})

function doLogout() {
  logout()
  router.push('/login')
}
</script>

<template>
  <header
    :class="[
      'sticky top-0 z-20 border-b transition-colors',
      transparent
        ? 'bg-transparent border-white/10'
        : 'bg-white border-slate-200',
    ]"
  >
    <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
      <div class="flex items-center gap-4">
        <RouterLink to="/" class="flex items-center gap-2 group">
          <div class="bg-plant-600 p-1.5 rounded-lg group-hover:bg-plant-500 transition-colors">
            <Sprout class="w-5 h-5 text-white" />
          </div>
          <span :class="['font-bold', transparent ? 'text-white' : 'text-slate-900']">
            Plant CPS
          </span>
        </RouterLink>

        <nav v-if="isLoggedIn" class="hidden sm:flex items-center gap-1 ml-2">
          <RouterLink
            to="/dashboard"
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              route.name === 'dashboard'
                ? (transparent ? 'bg-white/20 text-white' : 'bg-plant-50 text-plant-700')
                : (transparent ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'),
            ]"
          >
            <LayoutDashboard class="w-4 h-4" />
            Dashboard
          </RouterLink>
          <RouterLink
            to="/settings"
            :class="[
              'flex items-center gap-1.5 px-3 py-1.5 rounded-lg text-sm font-medium transition-colors',
              route.name === 'settings'
                ? (transparent ? 'bg-white/20 text-white' : 'bg-plant-50 text-plant-700')
                : (transparent ? 'text-white/70 hover:text-white hover:bg-white/10' : 'text-slate-500 hover:text-slate-900 hover:bg-slate-50'),
            ]"
          >
            <Settings class="w-4 h-4" />
            Settings
          </RouterLink>
        </nav>
      </div>

      <div v-if="isLoggedIn" class="flex items-center gap-2">
        <span
          :class="[
            'text-xs px-2 py-0.5 rounded-full',
            transparent ? 'bg-white/20 text-white' : 'bg-plant-50 text-plant-700',
          ]"
        >
          {{ authState.role }}
        </span>
        <Button
          severity="secondary"
          text
          size="small"
          @click="doLogout"
          aria-label="Logout"
        >
          <LogOut :class="['w-4 h-4', transparent ? 'text-white/70' : '']" />
        </Button>
      </div>
    </div>
  </header>
</template>
