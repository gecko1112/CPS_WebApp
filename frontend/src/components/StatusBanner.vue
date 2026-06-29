<script setup>
import { CheckCircle2, AlertTriangle, AlertOctagon, X } from 'lucide-vue-next'
import { computed, ref } from 'vue'

const props = defineProps({
  status: Object,
})

const collapsed = ref(false)

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
  <!-- Collapsed: slim bar with just a check sign. Click to re-expand. -->
  <button
    v-if="status && collapsed"
    type="button"
    @click="collapsed = false"
    :class="[config.bg, config.border, 'border rounded-full px-4 py-2 flex items-center gap-2 w-full sm:w-auto hover:brightness-110 transition']"
    aria-label="Show system status"
  >
    <CheckCircle2 :class="[config.iconColor, 'w-4 h-4 shrink-0']" />
    <span :class="[config.text, 'text-sm font-medium']">System status</span>
  </button>

  <!-- Expanded: full banner with an X to minimize. -->
  <div
    v-else-if="status"
    :class="[config.bg, config.border, 'border rounded-2xl p-4 sm:p-5 flex items-start gap-3']"
  >
    <component :is="config.icon" :class="[config.iconColor, 'w-6 h-6 shrink-0 mt-0.5']" />
    <div class="min-w-0 flex-1">
      <p :class="[config.text, 'font-semibold']">{{ status.message }}</p>
      <p class="text-sm text-white/40 mt-0.5">{{ lastWateredText }}</p>
    </div>
    <button
      type="button"
      @click="collapsed = true"
      class="shrink-0 -mt-1 -mr-1 p-1 text-white/40 hover:text-white/80 transition-colors"
      aria-label="Minimize status"
    >
      <X class="w-5 h-5" />
    </button>
  </div>
</template>
