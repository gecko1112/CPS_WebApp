<script setup>
// A little "plant-leaf" explainer bubble. Place inside a parent that has the
// `group relative` classes; an info dot shows in the corner and the bubble
// reveals on hover/focus.
import { Info } from 'lucide-vue-next'

defineProps({
  title: { type: String, default: '' },
  text: { type: String, default: '' },
  range: { type: String, default: '' },
})
</script>

<template>
  <div class="absolute top-2.5 right-2.5 z-20">
    <Info class="w-3.5 h-3.5 text-white/25 group-hover:text-plant-300 transition-colors" />
    <div
      class="pointer-events-none absolute right-0 bottom-full mb-2 w-56 z-30 opacity-0 translate-y-1 group-hover:opacity-100 group-hover:translate-y-0 transition-all duration-150"
    >
      <div
        class="relative rounded-2xl rounded-br-md bg-plant-900/95 backdrop-blur-md border border-plant-500/30 p-3 shadow-xl shadow-black/40 text-left"
      >
        <p v-if="title" class="text-xs font-semibold text-plant-300 mb-0.5">{{ title }}</p>
        <p class="text-xs text-white/75 leading-snug">{{ text }}</p>
        <p v-if="range" class="text-[11px] text-white/45 mt-1.5">
          Normal range: {{ range }}
        </p>
        <!-- little leaf-tip pointer -->
        <span
          class="absolute -bottom-1 right-4 w-2.5 h-2.5 rotate-45 bg-plant-900/95 border-r border-b border-plant-500/30"
        />
      </div>
    </div>
  </div>
</template>
