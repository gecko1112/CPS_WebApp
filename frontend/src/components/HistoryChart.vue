<script setup>
import { computed } from 'vue'
import HintBubble from './HintBubble.vue'

const props = defineProps({
  title: String,
  series: Array,
  color: { type: String, default: '#34d399' },
  unit: { type: String, default: '' },
  dark: { type: Boolean, default: false },
  hint: { type: String, default: '' },
  range: { type: String, default: '' },
  // Watering events ({ timestamp, trigger }) drawn as vertical 💧 markers.
  events: { type: Array, default: () => [] },
})

// Only annotate events inside the plotted time window (sky tone = water,
// matching the tank card; dashed line + 💧 so it never relies on color alone).
// The result is reference-memoized: the poll cycle replaces `series` every few
// seconds, and an unstable reference here would recompute chartOptions and
// force an ApexCharts updateOptions() (= flicker) on every poll.
let _annCache = { key: '', value: [] }
const eventAnnotations = computed(() => {
  const pts = props.series || []
  let xs = []
  if (pts.length && props.events.length) {
    const t0 = new Date(pts[0].t).getTime()
    const t1 = new Date(pts[pts.length - 1].t).getTime()
    xs = props.events
      .map((e) => new Date(e.timestamp).getTime())
      .filter((x) => x >= t0 && x <= t1)
  }
  const key = xs.join(',')
  if (key !== _annCache.key) {
    _annCache = {
      key,
      value: xs.map((x) => ({
        x,
        strokeDashArray: 4,
        borderColor: 'rgba(56, 189, 248, 0.7)',
        label: {
          text: '💧',
          borderWidth: 0,
          orientation: 'horizontal',
          offsetY: 6,
          style: { background: 'transparent', color: '#38bdf8', fontSize: '13px' },
        },
      })),
    }
  }
  return _annCache.value
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
  annotations: { xaxis: eventAnnotations.value },
}))

const chartSeries = computed(() => [
  {
    name: props.title,
    data: (props.series || []).map((p) => [new Date(p.t).getTime(), p.v]),
  },
])
</script>

<template>
  <div :class="[dark ? 'glass' : 'bg-white shadow-sm', 'rounded-2xl p-4 sm:p-5 group relative']">
    <HintBubble v-if="hint" :title="title" :text="hint" :range="range" />
    <div class="flex items-baseline justify-between mb-2">
      <h3 :class="['text-sm font-semibold', dark ? 'text-white/60' : 'text-slate-700']">
        {{ title }}
      </h3>
      <span
        v-if="eventAnnotations.length"
        :class="['text-[11px]', dark ? 'text-sky-300/70' : 'text-sky-600']"
      >
        💧 watering
      </span>
    </div>
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
