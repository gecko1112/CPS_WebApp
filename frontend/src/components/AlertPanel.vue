<script setup>
import { computed } from 'vue'
import { AlertTriangle, AlertOctagon, X } from 'lucide-vue-next'

const props = defineProps({
  // Array of { id, severity, code, plain_message, timestamp, active }
  alerts: { type: Array, default: () => [] },
})

const emit = defineEmits(['dismiss'])

const sorted = computed(() =>
  [...props.alerts].sort((a, b) => {
    // errors before warnings
    if (a.severity === b.severity) return 0
    return a.severity === 'error' ? -1 : 1
  })
)

const config = {
  error: {
    icon: AlertOctagon,
    bg: 'bg-rose-50',
    border: 'border-rose-300',
    iconColor: 'text-rose-600',
    labelColor: 'text-rose-800',
    badge: 'bg-rose-100 text-rose-700',
    label: 'Problem',
  },
  warning: {
    icon: AlertTriangle,
    bg: 'bg-amber-50',
    border: 'border-amber-300',
    iconColor: 'text-amber-600',
    labelColor: 'text-amber-800',
    badge: 'bg-amber-100 text-amber-700',
    label: 'Warning',
  },
}

function formatTime(iso) {
  return new Intl.DateTimeFormat(undefined, {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
  }).format(new Date(iso))
}
</script>

<template>
  <div v-if="sorted.length" class="space-y-2">
    <div
      v-for="alert in sorted"
      :key="alert.id"
      :class="[
        config[alert.severity].bg,
        config[alert.severity].border,
        'border rounded-2xl p-4 sm:p-5 flex items-start gap-3',
      ]"
    >
      <!-- Icon -->
      <component
        :is="config[alert.severity].icon"
        :class="[config[alert.severity].iconColor, 'w-6 h-6 shrink-0 mt-0.5']"
      />

      <!-- Text -->
      <div class="flex-1 min-w-0">
        <div class="flex items-center gap-2 flex-wrap">
          <span
            :class="[
              config[alert.severity].badge,
              'text-xs font-semibold px-2 py-0.5 rounded-full uppercase tracking-wide',
            ]"
          >
            {{ config[alert.severity].label }}
          </span>
          <span class="text-xs text-slate-500">{{ formatTime(alert.timestamp) }}</span>
        </div>
        <p :class="[config[alert.severity].labelColor, 'font-semibold mt-1']">
          {{ alert.plain_message }}
        </p>
      </div>

      <!-- Dismiss (visual only — real resolution goes via MQTT clear event) -->
      <button
        class="text-slate-400 hover:text-slate-600 shrink-0 mt-0.5"
        aria-label="Dismiss alert"
        @click="emit('dismiss', alert.id)"
      >
        <X class="w-4 h-4" />
      </button>
    </div>
  </div>
</template>
