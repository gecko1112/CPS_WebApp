<script setup>
import { computed } from 'vue'
import { Sprout } from 'lucide-vue-next'

const props = defineProps({
  health: { type: String, default: null }, // 'healthy' | 'needs_attention'
})

const healthy = computed(() => props.health === 'healthy')
</script>

<template>
  <div
    v-if="health"
    class="rounded-2xl p-5 sm:p-6 border flex items-center gap-4"
    :class="healthy
      ? 'bg-emerald-500/15 border-emerald-500/30'
      : 'bg-amber-500/15 border-amber-500/30'"
  >
    <div
      class="p-3 rounded-2xl shrink-0"
      :class="healthy ? 'bg-emerald-500/20' : 'bg-amber-500/20'"
    >
      <Sprout class="w-8 h-8" :class="healthy ? 'text-emerald-400' : 'text-amber-400'" />
    </div>
    <div class="min-w-0">
      <p class="text-xs uppercase tracking-wide text-white/40">Plant health</p>
      <p
        class="text-2xl sm:text-3xl font-bold"
        :class="healthy ? 'text-emerald-300' : 'text-amber-300'"
      >
        {{ healthy ? 'Healthy' : 'Needs attention' }}
      </p>
      <p class="text-sm text-white/50 mt-0.5">
        {{ healthy
          ? 'Your plant is doing great — no action needed.'
          : 'Something needs a look — check the alerts below.' }}
      </p>
    </div>
  </div>
</template>
