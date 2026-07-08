<script setup>
import { AlertTriangle, AlertCircle } from 'lucide-vue-next'

defineProps({
  alerts: { type: Array, default: () => [] },
})

function severityStyle(severity) {
  if (severity === 'critical') return 'bg-rose-500/15 border-rose-500/30 text-rose-300'
  return 'bg-amber-500/15 border-amber-500/30 text-amber-300'
}

function severityIcon(severity) {
  return severity === 'critical' ? AlertCircle : AlertTriangle
}

function typeLabel(alertType) {
  const labels = {
    sensor_fault: 'Sensor',
    process_fault: 'Process',
    system_fault: 'System',
  }
  return labels[alertType] || alertType
}

function timeAgo(iso) {
  const diff = Date.now() - new Date(iso).getTime()
  const mins = Math.floor(diff / 60000)
  if (mins < 1) return 'just now'
  if (mins < 60) return `${mins}m ago`
  return `${Math.floor(mins / 60)}h ago`
}

// Absolute local time (course requirement: alerts with timestamps).
// UTC from the backend, converted via Intl; date shown only when not today.
function fmtTime(iso) {
  const d = new Date(iso)
  const time = new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
  }).format(d)
  if (d.toDateString() === new Date().toDateString()) return time
  const day = new Intl.DateTimeFormat(undefined, {
    day: '2-digit',
    month: '2-digit',
  }).format(d)
  return `${day} ${time}`
}
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5">
    <h3 class="text-sm font-semibold text-white/60 mb-3">Active Alerts</h3>

    <div v-if="alerts.length === 0" class="text-sm text-white/30 py-6 text-center">
      No active alerts — system looks healthy
    </div>

    <div v-else class="space-y-2">
      <div
        v-for="(alert, i) in alerts"
        :key="i"
        :class="['rounded-lg border px-3 py-2.5 flex items-start gap-2.5', severityStyle(alert.severity)]"
      >
        <component
          :is="severityIcon(alert.severity)"
          class="w-4 h-4 mt-0.5 shrink-0"
        />
        <div class="min-w-0 flex-1">
          <div class="flex items-center gap-2 flex-wrap">
            <span class="text-xs font-semibold uppercase tracking-wide">
              {{ alert.severity }}
            </span>
            <span class="text-xs opacity-60">{{ typeLabel(alert.alert_type) }}</span>
            <span class="text-xs opacity-40 ml-auto tabular-nums">
              {{ fmtTime(alert.timestamp) }} · {{ timeAgo(alert.timestamp) }}
            </span>
          </div>
          <p class="text-sm mt-0.5 leading-snug text-white/80">{{ alert.description }}</p>
        </div>
      </div>
    </div>
  </div>
</template>
