<script setup>
import { computed } from 'vue'

const props = defineProps({
  title: String,
  series: Array, // [{t: ISO string, v: number}]
  color: { type: String, default: '#10b981' },
  unit: { type: String, default: '' },
})

const chartOptions = computed(() => ({
  chart: {
    type: 'area',
    toolbar: { show: false },
    zoom: { enabled: false },
    animations: { enabled: true, easing: 'linear', dynamicAnimation: { speed: 600 } },
    fontFamily: 'inherit',
  },
  stroke: { curve: 'smooth', width: 2 },
  fill: {
    type: 'gradient',
    gradient: { opacityFrom: 0.4, opacityTo: 0.05 },
  },
  dataLabels: { enabled: false },
  colors: [props.color],
  xaxis: {
    type: 'datetime',
    labels: { datetimeUTC: false },
  },
  yaxis: {
    labels: {
      formatter: (v) => `${Math.round(v)}${props.unit}`,
    },
  },
  tooltip: {
    x: { format: 'HH:mm:ss' },
    y: { formatter: (v) => `${v.toFixed(1)}${props.unit}` },
  },
  grid: { borderColor: '#e2e8f0', strokeDashArray: 4 },
}))

const chartSeries = computed(() => [
  {
    name: props.title,
    data: (props.series || []).map((p) => [new Date(p.t).getTime(), p.v]),
  },
])
</script>

<template>
  <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-5">
    <h3 class="text-sm font-semibold text-slate-700 mb-2">{{ title }}</h3>
    <apexchart
      v-if="series && series.length"
      type="area"
      height="220"
      :options="chartOptions"
      :series="chartSeries"
    />
    <p v-else class="text-sm text-slate-400 py-12 text-center">Waiting for data…</p>
  </div>
</template>
