<script setup>
import { Activity } from 'lucide-vue-next'

defineProps({
  // [{ id, label, online: true|false|null, last_seen, status }] — status is a
  // component-published data-quality string (e.g. P07: live/cached/unavailable)
  // shown instead of the generic online/offline text when present.
  components: { type: Array, default: () => [] },
})

function dotClass(c) {
  if (c.status) {
    if (c.status === 'live') return 'bg-emerald-400'
    if (c.status === 'unavailable') return 'bg-rose-500'
    return 'bg-amber-400' // cached & friends: usable but not fresh
  }
  if (c.online === true) return 'bg-emerald-400'
  if (c.online === false) return 'bg-rose-500'
  return 'bg-amber-400' // null = unknown
}
function stateText(c) {
  if (c.status) return c.status
  if (c.online === true) return 'online'
  if (c.online === false) return 'offline'
  return 'unknown'
}
function stateClass(c) {
  if (c.status) {
    if (c.status === 'live') return 'text-emerald-400'
    if (c.status === 'unavailable') return 'text-rose-400'
    return 'text-amber-400'
  }
  if (c.online === true) return 'text-emerald-400'
  if (c.online === false) return 'text-rose-400'
  return 'text-amber-400'
}
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5">
    <div class="flex items-center gap-2 mb-3">
      <Activity class="w-4 h-4 text-white/60" />
      <h3 class="text-sm font-semibold text-white/60">Component status</h3>
    </div>
    <div class="flex flex-wrap gap-2">
      <div
        v-for="c in components"
        :key="c.id"
        class="flex items-center gap-2 rounded-lg bg-white/5 px-3 py-1.5"
      >
        <span class="w-2 h-2 rounded-full shrink-0" :class="dotClass(c)" />
        <span
          class="text-sm"
          :class="c.online === false ? 'text-white/40' : 'text-white/75'"
        >
          {{ c.label }}
        </span>
        <span
          class="text-[10px] uppercase tracking-wide"
          :class="stateClass(c)"
        >
          {{ stateText(c) }}
        </span>
      </div>
    </div>
  </div>
</template>
