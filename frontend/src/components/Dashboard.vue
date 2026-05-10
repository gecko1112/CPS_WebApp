<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import { Droplet, Thermometer, Container, LogOut, Sprout } from 'lucide-vue-next'

import { api, authState, logout } from '../composables/useApi'
import SensorCard from './SensorCard.vue'
import StatusBanner from './StatusBanner.vue'
import HistoryChart from './HistoryChart.vue'

const latest = ref({ moisture: null, temperature: null, tank_level: null })
const status = ref(null)
const moistureHistory = ref([])
const tempHistory = ref([])

const showConfirm = ref(false)
const watering = ref(false)
const error = ref('')

const isOperator = computed(() => authState.value.role === 'operator')

let pollInterval = null

async function refresh() {
  try {
    const [l, s, mh, th] = await Promise.all([
      api.latest(),
      api.status(),
      api.history('moisture'),
      api.history('temperature'),
    ])
    latest.value = l
    status.value = s
    moistureHistory.value = mh
    tempHistory.value = th
  } catch (e) {
    error.value = e.message
    // If auth expired, kick back to login
    if (e.message.startsWith('401')) logout()
  }
}

async function confirmWater() {
  watering.value = true
  try {
    await api.water()
    showConfirm.value = false
    await refresh()
  } catch (e) {
    error.value = e.message
  } finally {
    watering.value = false
  }
}

onMounted(() => {
  refresh()
  // Poll every 3s in dev — bump to 10s+ in production
  pollInterval = setInterval(refresh, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

function fmt(v) {
  return v == null ? '—' : v.toFixed(1)
}
</script>

<template>
  <div class="min-h-screen">
    <!-- Header -->
    <header class="bg-white border-b border-slate-200 sticky top-0 z-10">
      <div class="max-w-5xl mx-auto px-4 py-3 flex items-center justify-between">
        <div class="flex items-center gap-2">
          <div class="bg-emerald-100 p-1.5 rounded-lg">
            <Sprout class="w-5 h-5 text-emerald-600" />
          </div>
          <h1 class="font-bold text-slate-900">Plant CPS</h1>
          <span class="text-xs px-2 py-0.5 rounded-full bg-slate-100 text-slate-600 ml-2">
            {{ authState.role }}
          </span>
        </div>
        <Button
          severity="secondary"
          text
          size="small"
          @click="logout"
          aria-label="Logout"
        >
          <LogOut class="w-4 h-4" />
        </Button>
      </div>
    </header>

    <main class="max-w-5xl mx-auto p-4 space-y-4">
      <!-- Status banner -->
      <StatusBanner :status="status" />

      <!-- Sensor cards: 1 col on mobile, 3 cols on desktop -->
      <div class="grid grid-cols-1 sm:grid-cols-3 gap-3 sm:gap-4">
        <SensorCard
          label="Soil moisture"
          :value="fmt(latest.moisture)"
          unit="%"
          :icon="Droplet"
          tone="emerald"
        />
        <SensorCard
          label="Temperature"
          :value="fmt(latest.temperature)"
          unit="°C"
          :icon="Thermometer"
          tone="amber"
        />
        <SensorCard
          label="Water tank"
          :value="fmt(latest.tank_level)"
          unit="%"
          :icon="Container"
          tone="sky"
        />
      </div>

      <!-- Action button -->
      <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-5 flex items-center justify-between gap-3">
        <div>
          <p class="font-semibold text-slate-900">Manual watering</p>
          <p class="text-sm text-slate-500">
            {{ isOperator ? 'Trigger a watering cycle now.' : 'Operator role required.' }}
          </p>
        </div>
        <Button
          label="Water now"
          severity="success"
          :disabled="!isOperator"
          @click="showConfirm = true"
        >
          <Droplet class="w-4 h-4 mr-2" />
          Water now
        </Button>
      </div>

      <!-- Charts -->
      <div class="grid grid-cols-1 md:grid-cols-2 gap-4">
        <HistoryChart
          title="Soil moisture (live)"
          :series="moistureHistory"
          color="#10b981"
          unit="%"
        />
        <HistoryChart
          title="Temperature (live)"
          :series="tempHistory"
          color="#f59e0b"
          unit="°C"
        />
      </div>

      <p v-if="error" class="text-sm text-rose-600">{{ error }}</p>
    </main>

    <!-- Confirmation dialog -->
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
