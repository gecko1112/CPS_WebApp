<script setup>
defineProps({
  label: String,
  value: [Number, String],
  unit: String,
  icon: Object,
  // Tailwind colour name e.g. 'emerald', 'sky', 'amber'
  tone: { type: String, default: 'slate' },
})

const toneClasses = {
  emerald: { bg: 'bg-emerald-50', text: 'text-emerald-600' },
  sky: { bg: 'bg-sky-50', text: 'text-sky-600' },
  amber: { bg: 'bg-amber-50', text: 'text-amber-600' },
  rose: { bg: 'bg-rose-50', text: 'text-rose-600' },
  slate: { bg: 'bg-slate-100', text: 'text-slate-600' },
}
</script>

<template>
  <div class="bg-white rounded-2xl shadow-sm p-4 sm:p-5 flex items-center gap-4">
    <div :class="[toneClasses[tone].bg, 'p-3 rounded-xl shrink-0']">
      <component :is="icon" :class="[toneClasses[tone].text, 'w-6 h-6']" />
    </div>
    <div class="min-w-0">
      <p class="text-xs sm:text-sm text-slate-500 truncate">{{ label }}</p>
      <p class="text-2xl sm:text-3xl font-bold text-slate-900">
        {{ value }}<span class="text-base font-medium text-slate-400 ml-0.5">{{ unit }}</span>
      </p>
    </div>
  </div>
</template>
