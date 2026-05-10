<script setup>
import { CheckCircle2, AlertTriangle, AlertOctagon } from 'lucide-vue-next'
import { computed } from 'vue'

const props = defineProps({
  status: Object, // { level, message, last_watered_at }
})

const config = computed(() => {
  switch (props.status?.level) {
    case 'ok':
      return { icon: CheckCircle2, bg: 'bg-emerald-50', border: 'border-emerald-200', text: 'text-emerald-800', iconColor: 'text-emerald-600' }
    case 'warning':
      return { icon: AlertTriangle, bg: 'bg-amber-50', border: 'border-amber-200', text: 'text-amber-800', iconColor: 'text-amber-600' }
    case 'error':
      return { icon: AlertOctagon, bg: 'bg-rose-50', border: 'border-rose-200', text: 'text-rose-800', iconColor: 'text-rose-600' }
    default:
      return { icon: CheckCircle2, bg: 'bg-slate-50', border: 'border-slate-200', text: 'text-slate-800', iconColor: 'text-slate-600' }
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
      <p class="text-sm text-slate-600 mt-0.5">{{ lastWateredText }}</p>
    </div>
  </div>
</template>
