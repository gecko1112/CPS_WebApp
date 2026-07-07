<script setup>
import { ref, onMounted, onUnmounted, computed } from 'vue'
import Button from 'primevue/button'
import Dialog from 'primevue/dialog'
import {
  Droplet, Thermometer, Container,
  BatteryCharging, Cpu,
} from 'lucide-vue-next'

import { api, authState, logout } from '../composables/useApi'
import { viewMode } from '../composables/useViewMode'
import { watchAlerts } from '../composables/useAlertWatcher'
import router from '../router'
import AppHeader from './AppHeader.vue'
import SensorCard from './SensorCard.vue'
import StatusBanner from './StatusBanner.vue'
import HistorySection from './HistorySection.vue'
import AlertPanel from './AlertPanel.vue'
import WateringHistory from './WateringHistory.vue'
import PlantProfile from './PlantProfile.vue'
import WeatherCard from './WeatherCard.vue'
import ComponentHealth from './ComponentHealth.vue'
import PlantHealth from './PlantHealth.vue'
import SystemDepiction from './SystemDepiction.vue'
import WaterBackground from './WaterBackground.vue'

const latest = ref(null)
const status = ref(null)
const alerts = ref([])
const moistureHistory = ref([])
const tempHistory = ref([])
const wateringEvents = ref([])
const wateringCfg = ref(null)
const components = ref([])
const historyRange = ref(24) // hours: 1 | 12 | 24
const showConfirm = ref(false)
const watering = ref(false)
const error = ref('')
const success = ref('')

const isOperator = computed(() => authState.value.role === 'operator')
const isAdvanced = computed(() => viewMode.value === 'advanced')

let pollInterval = null

async function refresh() {
  try {
    const [l, s, a, mh, th, wh, wc, co] = await Promise.all([
      api.latest(),
      api.status(),
      api.alertsActive(),
      api.history('moisture', 200, historyRange.value),
      api.history('temperature', 200, historyRange.value),
      api.wateringHistory(),
      api.wateringConfig(),
      api.components(),
    ])
    latest.value = l
    status.value = s
    alerts.value = a
    watchAlerts(a)
    moistureHistory.value = mh
    tempHistory.value = th
    wateringEvents.value = wh
    wateringCfg.value = wc
    components.value = co
  } catch (e) {
    error.value = e.message
    if (e.status === 401) { logout(); router.push('/login') }
  }
}

function setRange(h) {
  historyRange.value = h
  refresh()
}

async function saveProfile(payload) {
  error.value = ''
  try {
    await api.updateWateringConfig(payload)
    success.value = 'Watering profiles updated.'
    setTimeout(() => { success.value = '' }, 4000)
    await refresh()
  } catch (e) {
    error.value = e.message
  }
}

async function confirmWater() {
  watering.value = true
  error.value = ''
  try {
    await api.water()
    showConfirm.value = false
    success.value = 'Watering command sent.'
    setTimeout(() => { success.value = '' }, 4000)
    await refresh()
  } catch (e) {
    showConfirm.value = false
    error.value = e.message
  } finally {
    watering.value = false
  }
}

onMounted(() => {
  refresh()
  pollInterval = setInterval(refresh, 3000)
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})

function pct(v) {
  return v == null ? '—' : (v * 100).toFixed(1)
}
function fmt(v) {
  return v == null ? '—' : v.toFixed(1)
}
function fmtHours(h) {
  if (h == null) return '—'
  if (h < 1) return `${Math.round(h * 60)}min`
  if (h < 48) return `${h.toFixed(0)}h`
  return `${(h / 24).toFixed(1)}d`
}
</script>

<template>
  <div class="min-h-screen bg-slate-950 relative overflow-hidden">
    <!-- Greyish / translucent water-droplet backdrop -->
    <WaterBackground />

    <div class="relative z-10">
      <AppHeader transparent />

      <main class="max-w-7xl mx-auto p-4">
        <div class="grid grid-cols-1 lg:grid-cols-3 gap-4 items-start">
          <!-- Left column: main content -->
          <div class="lg:col-span-2 space-y-4">
        <!-- Plant health headline (most important for the everyday user) -->
        <PlantHealth :health="status?.plant_health" />

        <!-- Status banner -->
        <StatusBanner :status="status" />

        <!-- Key stats (both views) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3 sm:gap-4">
          <SensorCard
            label="Soil moisture"
            :value="latest ? pct(latest.soil_moisture.calibrated) : '—'"
            unit="%"
            :icon="Droplet"
            tone="emerald"
            :sub="isAdvanced && latest && latest.soil_moisture.raw_adc != null ? `raw ADC ${latest.soil_moisture.raw_adc}` : ''"
            hint="How wet the soil is right now, from the calibrated moisture sensor. 0% is bone dry, 100% is fully saturated."
            range="40–70% for most plants"
          />
          <SensorCard
            label="Temperature"
            :value="latest ? fmt(latest.weather.temperature_c) : '—'"
            unit="°C"
            :icon="Thermometer"
            tone="amber"
            hint="Air temperature near the plant, from the weather service."
            range="18–26 °C for most houseplants"
          />
          <SensorCard
            label="Water tank"
            :value="latest ? fmt(latest.tank.level_pct) : '—'"
            unit="%"
            :icon="Container"
            tone="sky"
            :sub="isAdvanced && latest && latest.tank.sensor_distance_mm != null ? `dist ${fmt(latest.tank.sensor_distance_mm)} mm` : ''"
            hint="How full the water reservoir is. When it runs low, refill it or watering will be suppressed."
            range="keep above 25%"
          />
          <WeatherCard :weather="latest ? latest.weather : null" :advanced="isAdvanced" />
        </div>

        <!-- Expert stats (advanced view only) -->
        <div v-if="isAdvanced" class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <SensorCard
            label="Controller"
            :value="latest ? latest.controller.state : '—'"
            unit=""
            :icon="Cpu"
            tone="violet"
            :sub="latest && latest.controller.reason ? latest.controller.reason : ''"
            hint="What the watering controller is doing: idle, watering, soaking, suppressed (e.g. rain expected), or error."
          />
          <SensorCard
            label="Battery"
            :value="latest ? fmt(latest.power.battery_soc) : '—'"
            unit="%"
            :icon="BatteryCharging"
            tone="lime"
            :sub="latest && latest.power.mode ? `mode ${latest.power.mode}` : ''"
            hint="Charge of the solar battery that powers the sensors and pump. Low battery reduces non-essential activity."
            range="above 20%"
          />
        </div>

        <!-- Whole-system depiction: tank level + pump activity + plant -->
        <SystemDepiction
          v-if="latest"
          :tank="latest.tank"
          :controller="latest.controller"
        />

        <!-- Manual watering (+ tank time-to-empty in expert view) -->
        <div class="grid grid-cols-1 sm:grid-cols-2 gap-3 sm:gap-4">
          <div v-if="isAdvanced" class="glass rounded-2xl p-4 sm:p-5">
            <p class="text-sm text-white/50 mb-1">Tank time to empty</p>
            <p class="text-2xl font-bold text-white">
              {{ latest ? fmtHours(latest.tank_forecast.time_to_empty_h) : '—' }}
            </p>
          </div>

          <div
            class="glass rounded-2xl p-4 sm:p-5 flex items-center justify-between gap-3"
            :class="!isAdvanced ? 'sm:col-span-2' : ''"
          >
            <div>
              <p class="font-semibold text-white">Manual watering</p>
              <p class="text-sm text-white/50">
                {{ isOperator ? 'Trigger a watering cycle now.' : 'Operator role required.' }}
              </p>
            </div>
            <Button
              label="Water now"
              :disabled="!isOperator"
              @click="showConfirm = true"
              class="!bg-plant-600 !border-plant-600 hover:!bg-plant-500 !rounded-xl shrink-0"
            >
              <Droplet class="w-4 h-4 mr-2" />
              Water now
            </Button>
          </div>
        </div>

        <!-- Component status (advanced) -->
        <ComponentHealth v-if="isAdvanced" :components="components" />

        <!-- Plant profiles (operator-editable) + watering history (advanced) -->
        <div
          class="grid grid-cols-1 gap-3 sm:gap-4"
          :class="isAdvanced ? 'lg:grid-cols-2' : ''"
        >
          <PlantProfile
            :config="wateringCfg"
            :is-operator="isOperator"
            :advanced="isAdvanced"
            @save="saveProfile"
          />
          <WateringHistory v-if="isAdvanced" :events="wateringEvents" />
        </div>

        <!-- History — side-by-side here in expert view; in simple view the
             charts sit under the alerts on the right instead. -->
        <HistorySection
          v-if="isAdvanced"
          :moisture="moistureHistory"
          :temperature="tempHistory"
          :watering="wateringEvents"
          :range="historyRange"
          @set-range="setRange"
        />

        <p v-if="error" class="text-sm text-rose-400">{{ error }}</p>
        <p v-if="success" class="text-sm text-plant-300">{{ success }}</p>
          </div>

          <!-- Right column: alerts; in simple view the graphs stack under them -->
          <aside class="lg:col-span-1 space-y-4">
            <AlertPanel :alerts="alerts" />
            <HistorySection
              v-if="!isAdvanced"
              stacked
              :moisture="moistureHistory"
              :temperature="tempHistory"
              :watering="wateringEvents"
              :range="historyRange"
              @set-range="setRange"
            />
          </aside>
        </div>
      </main>
    </div>

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
        <Button
          label="Yes, water now"
          :loading="watering"
          @click="confirmWater"
          class="!bg-plant-600 !border-plant-600 hover:!bg-plant-500"
        />
      </div>
    </Dialog>
  </div>
</template>
