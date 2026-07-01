<script setup>
import { computed } from 'vue'
import {
  Sun, CloudSun, Cloud, CloudDrizzle, CloudRain, CloudLightning, CloudOff,
} from 'lucide-vue-next'

const props = defineProps({
  weather: { type: Object, default: null },
  advanced: { type: Boolean, default: false },
})

// condition id (from the backend) -> icon + label + colour
const MAP = {
  sunny: { icon: Sun, label: 'Sunny', color: 'text-amber-400' },
  partly_cloudy: { icon: CloudSun, label: 'Partly cloudy', color: 'text-amber-300' },
  cloudy: { icon: Cloud, label: 'Cloudy', color: 'text-slate-300' },
  light_rain: { icon: CloudDrizzle, label: 'Light rain', color: 'text-sky-300' },
  rainy: { icon: CloudRain, label: 'Rainy', color: 'text-sky-400' },
  stormy: { icon: CloudLightning, label: 'Stormy', color: 'text-indigo-300' },
  unknown: { icon: CloudOff, label: 'No forecast', color: 'text-white/40' },
}

const w = computed(() => props.weather)
const cond = computed(() => MAP[w.value?.condition] || MAP.unknown)
const hasData = computed(
  () => w.value && w.value.condition && w.value.condition !== 'unknown'
    && w.value.status !== 'unavailable',
)
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5 flex items-center gap-4">
    <component :is="cond.icon" :class="[cond.color, 'w-10 h-10 shrink-0']" />
    <div class="min-w-0">
      <p class="text-xs sm:text-sm text-white/50 truncate">
        Weather · {{ w?.horizon_label || 'forecast' }}
      </p>
      <p class="text-lg sm:text-xl font-bold text-white truncate">{{ cond.label }}</p>
      <p v-if="hasData" class="text-xs text-white/40 truncate">
        <span v-if="w.temperature_c != null">{{ Math.round(w.temperature_c) }}°C</span>
        <span v-if="w.precipitation_mm != null"> · {{ w.precipitation_mm.toFixed(1) }} mm rain</span>
        <span v-if="advanced && w.solar_radiation_wm2 != null" class="font-mono">
          · {{ Math.round(w.solar_radiation_wm2) }} W/m²
        </span>
      </p>
      <p v-else class="text-xs text-white/30">forecast unavailable</p>
    </div>
  </div>
</template>