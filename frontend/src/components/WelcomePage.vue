<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import { RouterLink } from 'vue-router'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import {
  Droplet, ArrowRight, AlertTriangle,
  CheckCircle, XCircle, CloudRain, Sprout, BatteryCharging,
  LayoutDashboard,
} from 'lucide-vue-next'

import { api, authState } from '../composables/useApi'
import AppHeader from './AppHeader.vue'

const status = ref(null)
const latest = ref(null)
const alerts = ref([])
const showConfirm = ref(false)
const watering = ref(false)

const isOperator = computed(() => authState.value.role === 'operator')

let pollInterval = null

async function refresh() {
  try {
    const [s, l, a] = await Promise.all([
      api.status(),
      api.latest(),
      api.alertsActive(),
    ])
    status.value = s
    latest.value = l
    alerts.value = a
  } catch { /* ignore — next tick will retry */ }
}

async function confirmWater() {
  watering.value = true
  try {
    await api.water()
    showConfirm.value = false
    await refresh()
  } catch { /* ignore */ }
  finally { watering.value = false }
}

onMounted(() => {
  refresh()
  pollInterval = setInterval(refresh, 5000)
})
onUnmounted(() => { if (pollInterval) clearInterval(pollInterval) })

function statusIcon(level) {
  if (level === 'ok') return CheckCircle
  if (level === 'error') return XCircle
  return AlertTriangle
}
function statusColor(level) {
  if (level === 'ok') return 'text-plant-400'
  if (level === 'error') return 'text-rose-400'
  return 'text-amber-400'
}
function pct(v) {
  return v == null ? '—' : (v * 100).toFixed(0)
}
function fmt(v) {
  return v == null ? '—' : v.toFixed(1)
}
</script>

<template>
  <div class="relative min-h-screen bg-plant-950 overflow-hidden">
    <!-- Video background (drop plant-bg.mp4 into frontend/public/) -->
    <video
      autoplay muted loop playsinline
      class="absolute inset-0 w-full h-full video-bg pointer-events-none"
      src="/plant-bg.mp4"
      @error="$event.target.style.display='none'"
    />

    <!-- Animated blob fallback (shows when video is missing) -->
    <div class="absolute inset-0 overflow-hidden">
      <div class="blob w-[600px] h-[600px] bg-plant-700/40 -top-40 -left-40" style="animation-delay: 0s" />
      <div class="blob w-[500px] h-[500px] bg-plant-500/30 top-1/2 -right-32" style="animation-delay: -7s" />
      <div class="blob w-[400px] h-[400px] bg-emerald-600/25 -bottom-20 left-1/3" style="animation-delay: -14s" />
    </div>

    <!-- Dark overlay -->
    <div class="absolute inset-0 bg-gradient-to-b from-plant-950/60 via-plant-950/40 to-plant-950/80" />

    <!-- Header -->
    <div class="relative z-10">
      <AppHeader transparent />
    </div>

    <!-- Content -->
    <main class="relative z-10 max-w-5xl mx-auto px-4 pt-8 sm:pt-16 pb-12">
      <!-- Hero -->
      <div class="text-center mb-10 sm:mb-16">
        <div class="inline-flex items-center gap-2 bg-plant-500/20 border border-plant-400/30 rounded-full px-4 py-1.5 mb-6">
          <Sprout class="w-4 h-4 text-plant-400" />
          <span class="text-sm text-plant-300 font-medium">Autonomous Plant Watering System</span>
        </div>
        <h1 class="text-4xl sm:text-6xl font-bold text-white tracking-tight mb-4">
          Your plants,<br>
          <span class="text-plant-400">taken care of.</span>
        </h1>
        <p class="text-lg text-white/50 max-w-lg mx-auto">
          Monitor soil moisture, weather forecasts, and system health — all from your phone.
        </p>
      </div>

      <!-- Status cards grid -->
      <div class="grid grid-cols-2 sm:grid-cols-4 gap-3 sm:gap-4 mb-8">
        <!-- System status -->
        <div class="glass rounded-2xl p-4 sm:p-5">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-2">System</p>
          <div v-if="status" class="flex items-center gap-2">
            <component :is="statusIcon(status.level)" :class="['w-6 h-6', statusColor(status.level)]" />
            <span class="text-lg font-bold text-white capitalize">{{ status.level }}</span>
          </div>
          <div v-else class="h-7 bg-white/5 rounded animate-pulse" />
        </div>

        <!-- Soil moisture -->
        <div class="glass rounded-2xl p-4 sm:p-5">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-2">Soil moisture</p>
          <p class="text-3xl font-bold text-white">
            {{ latest ? pct(latest.soil_moisture.calibrated) : '—' }}
            <span class="text-base font-normal text-white/40">%</span>
          </p>
        </div>

        <!-- Rain forecast -->
        <div class="glass rounded-2xl p-4 sm:p-5">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-2">Rain forecast</p>
          <div v-if="latest" class="flex items-center gap-2">
            <CloudRain class="w-5 h-5 text-blue-400" />
            <span class="text-lg font-bold text-white">
              {{ latest.weather.status === 'fresh' ? fmt(latest.weather.rainfall_mm) + ' mm' : 'N/A' }}
            </span>
          </div>
          <div v-else class="h-7 bg-white/5 rounded animate-pulse" />
        </div>

        <!-- Active alerts -->
        <div class="glass rounded-2xl p-4 sm:p-5">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-2">Alerts</p>
          <div class="flex items-center gap-2">
            <span :class="['text-3xl font-bold', alerts.length > 0 ? 'text-amber-400' : 'text-white']">
              {{ alerts.length }}
            </span>
            <span class="text-sm text-white/40">active</span>
          </div>
        </div>
      </div>

      <!-- Secondary info row -->
      <div class="grid grid-cols-3 gap-3 sm:gap-4 mb-10">
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-1">Tank</p>
          <p class="text-xl font-bold text-white">
            {{ latest ? fmt(latest.tank.level_pct) : '—' }}
            <span class="text-sm font-normal text-white/40">%</span>
          </p>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-1">Battery</p>
          <p class="text-xl font-bold text-white">
            {{ latest ? fmt(latest.power.battery_soc) : '—' }}
            <span class="text-sm font-normal text-white/40">%</span>
          </p>
        </div>
        <div class="glass rounded-2xl p-4">
          <p class="text-xs text-white/40 uppercase tracking-wide mb-1">Last watered</p>
          <p class="text-sm font-bold text-white">
            {{ status?.last_watered_at ? new Date(status.last_watered_at).toLocaleTimeString() : 'Not yet' }}
          </p>
        </div>
      </div>

      <!-- CTAs -->
      <div class="flex flex-col sm:flex-row items-center justify-center gap-3">
        <RouterLink to="/dashboard" class="w-full sm:w-auto">
          <Button
            class="w-full !bg-plant-600 !border-plant-600 hover:!bg-plant-500 !text-white !font-semibold !px-8 !py-3 !text-base !rounded-xl"
          >
            <LayoutDashboard class="w-5 h-5 mr-2" />
            Open Dashboard
            <ArrowRight class="w-4 h-4 ml-2" />
          </Button>
        </RouterLink>

        <Button
          v-if="isOperator"
          class="w-full sm:w-auto !bg-white/10 !border-white/20 hover:!bg-white/20 !text-white !font-semibold !px-8 !py-3 !text-base !rounded-xl"
          @click="showConfirm = true"
        >
          <Droplet class="w-5 h-5 mr-2" />
          Water Now
        </Button>
      </div>
    </main>

    <!-- Water confirmation dialog -->
    <Dialog
      v-model:visible="showConfirm"
      modal
      header="Confirm watering"
      :style="{ width: '90vw', maxWidth: '420px' }"
    >
      <p class="text-slate-700 mb-4">
        This will start the water pump immediately. Make sure the tank has enough water.
      </p>
      <div class="flex justify-end gap-2">
        <Button label="Cancel" severity="secondary" text @click="showConfirm = false" />
        <Button label="Yes, water now" severity="success" :loading="watering" @click="confirmWater" />
      </div>
    </Dialog>
  </div>
</template>

