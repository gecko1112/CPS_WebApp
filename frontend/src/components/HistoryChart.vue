<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  series: Array,
  color: { type: String, default: '#34d399' },
  unit: { type: String, default: '' },
  dark: { type: Boolean, default: false },
})

const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 600 } },
    fontFamily: 'inherit',
    background: 'transparent',
  },
  theme: { mode: props.dark ? 'dark' : 'light' },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { opacityFrom: 0.35, opacityTo: 0.0 },
  },
  dataLabels: { enabled: false },
  colors: [props.color],
  xaxis: {
    type: 'datetime',
    labels: {
      datetimeUTC: false,
      style: { colors: props.dark ? 'rgba(255,255,255,0.4)' : '#94a3b8' },
    },
    axisBorder: { color: props.dark ? 'rgba(255,255,255,0.1)' : '#e2e8f0' },
    axisTicks: { color: props.dark ? 'rgba(255,255,255,0.1)' : '#e2e8f0' },
  },
  yaxis: {
    labels: {
      formatter: (v) => `${Math.round(v)}${props.unit}`,
      style: { colors: props.dark ? 'rgba(255,255,255,0.4)' : '#94a3b8' },
    },
  },
  tooltip: {
    theme: props.dark ? 'dark' : 'light',
    x: { format: 'HH:mm:ss' },
    y: { formatter: (v) => `${v.toFixed(1)}${props.unit}` },
  },
  grid: {
    borderColor: props.dark ? 'rgba(255,255,255,0.07)' : '#e2e8f0',
    strokeDashArray: 4,
  },
}))

const chartSeries = computed(() => [
  {
    name: props.title,
    data: (props.series || []).map((p) => [new Date(p.t).getTime(), p.v]),
  },
])
</script>

<template>
  <div :class="[dark ? 'glass' : 'bg-white shadow-sm', 'rounded-2xl p-4 sm:p-5']">
    <h3 :class="['text-sm font-semibold mb-2', dark ? 'text-white/60' : 'text-slate-700']">
      {{ title }}
    </h3>
    <apexchart
      v-if="series && series.length"
      type="area"
      height="220"
      :options="chartOptions"
      :series="chartSeries"
    />
    <p v-else :class="['text-sm py-12 text-center', dark ? 'text-white/30' : 'text-slate-400']">
      Waiting for data…
    </p>
  </div>
</template>
