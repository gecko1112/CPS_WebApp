<script setup>
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps({
  status: Object,
})

const config = computed(() => {
  switch (props.status?.level) {
    case 'ok':
      return { icon: CheckCircle2, bg: 'bg-emerald-500/15', border: 'border-emerald-500/30', text: 'text-emerald-300', iconColor: 'text-emerald-400' }
    case 'warning':
      return { icon: AlertTriangle, bg: 'bg-amber-500/15', border: 'border-amber-500/30', text: 'text-amber-300', iconColor: 'text-amber-400' }
    case 'error':
      return { icon: AlertOctagon, bg: 'bg-rose-500/15', border: 'border-rose-500/30', text: 'text-rose-300', iconColor: 'text-rose-400' }
    default:
      return { icon: CheckCircle2, bg: 'bg-white/5', border: 'border-white/10', text: 'text-white/60', iconColor: 'text-white/40' }
  }
})

const lastWateredText = computed(() => {
  if (!props.status?.last_watered_at) return 'Not watered yet in this session'
  const date = new Date(props.status.last_watered_at)
  return `Last watered: ${date.toLocaleString()}`
})
</script>

<template>
  <div
    v-if="status"
    :class="[config.bg, config.border, 'border rounded-2xl p-4 sm:p-5 flex items-start gap-3']"
  >
    <component :is="config.icon" :class="[config.iconColor, 'w-6 h-6 shrink-0 mt-0.5']" />
    <div class="min-w-0">
      <p :class="[config.text, 'font-semibold']">{{ status.message }}</p>
      <p class="text-sm text-white/40 mt-0.5">{{ lastWateredText }}</p>
    </div>
  </div>
</template>
