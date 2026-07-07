<script setup>
import HistoryChart from './HistoryChart.vue'

defineProps({
  moisture: { type: Array, default: () => [] },
  temperature: { type: Array, default: () => [] },
  watering: { type: Array, default: () => [] }, // watering events → 💧 markers
  range: { type: Number, default: 24 }, // hours
  stacked: { type: Boolean, default: false }, // stacked vs. side-by-side
})
const emit = defineEmits(['set-range'])

const RANGES = [
  { h: 1, l: '1h' },
  { h: 12, l: '12h' },
  { h: 24, l: '24h' },
]
</script>

<template>
  <div class="space-y-3">
    <div class="flex items-center justify-between">
      <h3 class="text-sm font-semibold text-white/60">History</h3>
      <div class="flex items-center rounded-lg bg-white/10 p-0.5 text-xs font-medium">
        <button
          v-for="opt in RANGES"
          :key="opt.h"
          type="button"
          @click="emit('set-range', opt.h)"
          :class="[
            'px-2.5 py-1 rounded-md transition-colors',
            range === opt.h ? 'bg-white/20 text-white' : 'text-white/50 hover:text-white',
          ]"
        >
          {{ opt.l }}
        </button>
      </div>
    </div>

    <div class="grid grid-cols-1 gap-4" :class="stacked ? '' : 'md:grid-cols-2'">
      <HistoryChart
        title="Soil moisture"
        :series="moisture"
        :events="watering"
        color="#34d399"
        unit="%"
        dark
        hint="Soil moisture trend over the selected window. Watch for it dropping toward the dry threshold before a watering. 💧 marks a watering event."
        range="40–70%"
      />
      <HistoryChart
        title="Temperature"
        :series="temperature"
        color="#fbbf24"
        unit="°C"
        dark
        hint="Air temperature trend over the selected window."
        range="18–26 °C"
      />
    </div>
  </div>
</template>
