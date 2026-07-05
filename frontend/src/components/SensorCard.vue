<script setup>
import HintBubble from './HintBubble.vue'

defineProps({
  label: String,
  value: [Number, String],
  unit: String,
  icon: Object,
  tone: { type: String, default: 'slate' },
  sub: { type: String, default: '' }, // raw/detail line shown in advanced view
  hint: { type: String, default: '' }, // explainer shown on hover
  range: { type: String, default: '' }, // normal range shown in the hint
})

const toneClasses = {
  emerald: 'bg-emerald-500/20 text-emerald-400',
  sky: 'bg-sky-500/20 text-sky-400',
  amber: 'bg-amber-500/20 text-amber-400',
  rose: 'bg-rose-500/20 text-rose-400',
  slate: 'bg-white/10 text-white/60',
  violet: 'bg-violet-500/20 text-violet-400',
  blue: 'bg-blue-500/20 text-blue-400',
  lime: 'bg-lime-500/20 text-lime-400',
}
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5 flex items-center gap-4 group relative">
    <HintBubble v-if="hint" :title="label" :text="hint" :range="range" />
    <div :class="[toneClasses[tone]?.split(' ')[0] || 'bg-white/10', 'p-3 rounded-xl shrink-0']">
      <component :is="icon" :class="[toneClasses[tone]?.split(' ')[1] || 'text-white/60', 'w-6 h-6']" />
    </div>
    <div class="min-w-0">
      <p class="text-xs sm:text-sm text-white/50 truncate">{{ label }}</p>
      <p class="text-2xl sm:text-3xl font-bold text-white">
        {{ value }}<span class="text-base font-medium text-white/30 ml-0.5">{{ unit }}</span>
      </p>
      <p v-if="sub" class="text-xs text-white/35 mt-0.5 font-mono truncate">{{ sub }}</p>
    </div>
  </div>
</template>
