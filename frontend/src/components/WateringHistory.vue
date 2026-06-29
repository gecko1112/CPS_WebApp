<script setup>
import { History } from 'lucide-vue-next'

defineProps({
  events: { type: Array, default: () => [] },
})

function fmtTime(iso) {
  return new Date(iso).toLocaleString()
}
function triggerLabel(t) {
  return { manual: 'Manual', auto: 'Automatic', scheduled: 'Scheduled' }[t] || t
}
function pct(v) {
  return v == null ? null : `${(v * 100).toFixed(0)}%`
}
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5">
    <div class="flex items-center gap-2 mb-3">
      <History class="w-4 h-4 text-white/60" />
      <h3 class="text-sm font-semibold text-white/60">Watering history</h3>
    </div>

    <div v-if="events.length === 0" class="text-sm text-white/30 py-4 text-center">
      No watering events recorded yet
    </div>

    <div v-else class="space-y-1.5 max-h-72 overflow-y-auto">
      <div
        v-for="(e, i) in events"
        :key="i"
        class="flex items-center justify-between gap-3 rounded-lg bg-white/5 px-3 py-2"
      >
        <div class="min-w-0">
          <p class="text-sm text-white/80">{{ fmtTime(e.timestamp) }}</p>
          <p class="text-xs text-white/40">
            {{ e.duration_s }}s
            <span v-if="pct(e.moisture_before) && pct(e.moisture_after)">
              · {{ pct(e.moisture_before) }} → {{ pct(e.moisture_after) }}
            </span>
          </p>
        </div>
        <span
          class="text-xs px-2 py-0.5 rounded-full shrink-0"
          :class="e.trigger === 'manual'
            ? 'bg-plant-500/20 text-plant-300'
            : 'bg-white/10 text-white/50'"
        >
          {{ triggerLabel(e.trigger) }}
        </span>
      </div>
    </div>
  </div>
</template>
