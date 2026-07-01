<script setup>
import { AlertTriangle, AlertCircle, Info, X } from 'lucide-vue-next'
import { toasts, dismissToast } from '../composables/useToasts'

const STYLES = {
  critical: { icon: AlertCircle, box: 'border-rose-500/40 bg-rose-500/15', accent: 'text-rose-400' },
  warning: { icon: AlertTriangle, box: 'border-amber-500/40 bg-amber-500/15', accent: 'text-amber-400' },
  info: { icon: Info, box: 'border-sky-500/40 bg-sky-500/15', accent: 'text-sky-400' },
}
function style(sev) {
  return STYLES[sev] || STYLES.info
}
</script>

<template>
  <div
    class="fixed top-4 right-4 z-50 flex flex-col gap-2 w-[90vw] max-w-sm pointer-events-none"
  >
    <TransitionGroup name="toast">
      <div
        v-for="t in toasts"
        :key="t.id"
        class="pointer-events-auto backdrop-blur-md border rounded-xl p-3 flex items-start gap-2.5 shadow-lg shadow-black/30"
        :class="style(t.severity).box"
      >
        <component
          :is="style(t.severity).icon"
          class="w-5 h-5 shrink-0 mt-0.5"
          :class="style(t.severity).accent"
        />
        <div class="min-w-0 flex-1">
          <p class="text-sm font-semibold text-white">{{ t.title }}</p>
          <p v-if="t.message" class="text-xs text-white/70 mt-0.5 leading-snug">
            {{ t.message }}
          </p>
        </div>
        <button
          type="button"
          @click="dismissToast(t.id)"
          class="shrink-0 -mt-0.5 -mr-0.5 p-0.5 text-white/40 hover:text-white/80 transition-colors"
          aria-label="Dismiss"
        >
          <X class="w-4 h-4" />
        </button>
      </div>
    </TransitionGroup>
  </div>
</template>

<style scoped>
.toast-enter-active,
.toast-leave-active {
  transition: all 0.3s ease;
}
.toast-enter-from,
.toast-leave-to {
  opacity: 0;
  transform: translateX(1rem);
}
</style>
