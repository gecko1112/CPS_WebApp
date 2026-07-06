<script setup>
import { computed } from 'vue'

const props = defineProps({
  // { level_pct } from the tank slot
  tank: { type: Object, default: null },
  // { state } from the controller slot
  controller: { type: Object, default: null },
})

const level = computed(() => {
  const v = props.tank?.level_pct
  return typeof v === 'number' ? Math.max(0, Math.min(100, v)) : null
})

// Tank inner drawing area: y 52..164 (height 112).
const INNER_TOP = 52
const INNER_H = 112
const waterHeight = computed(() => (level.value == null ? 0 : (INNER_H * level.value) / 100))
const waterY = computed(() => INNER_TOP + (INNER_H - waterHeight.value))

const watering = computed(() =>
  ['watering', 'soaking'].includes(props.controller?.state),
)
const levelText = computed(() => (level.value == null ? '—' : `${Math.round(level.value)}%`))
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5">
    <h3 class="text-sm font-semibold text-white/60 mb-2">System overview</h3>

    <svg viewBox="0 0 420 210" class="w-full h-auto" :class="{ 'is-watering': watering }">
      <defs>
        <linearGradient id="water" x1="0" y1="0" x2="0" y2="1">
          <stop offset="0%" stop-color="#38bdf8" stop-opacity="0.9" />
          <stop offset="100%" stop-color="#0ea5e9" stop-opacity="0.75" />
        </linearGradient>
        <clipPath id="tankClip">
          <rect x="28" y="52" width="76" height="112" rx="6" />
        </clipPath>
      </defs>

      <!-- ===== Water tank ===== -->
      <rect x="24" y="48" width="84" height="120" rx="9"
            fill="rgba(255,255,255,0.04)" stroke="rgba(255,255,255,0.25)" stroke-width="2" />
      <g clip-path="url(#tankClip)">
        <rect x="28" :y="waterY" width="76" :height="waterHeight" fill="url(#water)"
              class="water-fill" />
      </g>
      <text x="66" y="120" text-anchor="middle" class="lvl">{{ levelText }}</text>
      <text x="66" y="184" text-anchor="middle" class="cap">Tank</text>

      <!-- ===== Pipe: tank -> pump -> plant ===== -->
      <path d="M108 150 H186 M234 150 H300 V150"
            fill="none" stroke="rgba(255,255,255,0.2)" stroke-width="8" stroke-linecap="round" />
      <!-- animated flow (only visible while watering) -->
      <path d="M108 150 H186 M234 150 H300"
            fill="none" stroke="#38bdf8" stroke-width="4" stroke-linecap="round"
            stroke-dasharray="2 12" class="flow" />

      <!-- ===== Pump ===== -->
      <circle cx="210" cy="150" r="24"
              fill="rgba(255,255,255,0.06)" stroke="rgba(255,255,255,0.3)" stroke-width="2" />
      <g transform="translate(210 150)">
        <g class="impeller">
          <g stroke="rgba(255,255,255,0.55)" stroke-width="3" stroke-linecap="round">
            <line x1="0" y1="-11" x2="0" y2="11" />
            <line x1="-11" y1="0" x2="11" y2="0" />
            <line x1="-8" y1="-8" x2="8" y2="8" />
            <line x1="-8" y1="8" x2="8" y2="-8" />
          </g>
          <circle r="3" fill="rgba(255,255,255,0.8)" />
        </g>
      </g>
      <text x="210" y="192" text-anchor="middle" class="cap">Pump</text>

      <!-- ===== Active indicator above the pump (rotating rings) ===== -->
      <g class="active-badge" transform="translate(210 104)">
        <circle r="15" fill="none" stroke="#34d399" stroke-width="2.5"
                stroke-dasharray="10 8" class="ring ring-a" />
        <circle r="9" fill="none" stroke="#6ee7b7" stroke-width="2.5"
                stroke-dasharray="6 6" class="ring ring-b" />
      </g>

      <!-- ===== Plant ===== -->
      <!-- pot -->
      <path d="M306 152 L354 152 L347 184 L313 184 Z"
            fill="rgba(180,83,9,0.35)" stroke="rgba(251,146,60,0.5)" stroke-width="1.5" />
      <rect x="304" y="148" width="52" height="7" rx="3"
            fill="rgba(180,83,9,0.5)" stroke="rgba(251,146,60,0.5)" stroke-width="1" />
      <!-- stem + leaves -->
      <g stroke="#34d399" stroke-width="3" fill="none" stroke-linecap="round">
        <path d="M330 148 C330 130 330 120 330 108" />
      </g>
      <path d="M330 126 C316 122 310 110 322 104 C332 110 332 120 330 126 Z" fill="#34d399" />
      <path d="M330 118 C344 114 350 102 338 96 C328 102 328 112 330 118 Z" fill="#10b981" />
      <path d="M330 110 C322 100 326 90 332 92 C336 98 334 106 330 110 Z" fill="#6ee7b7" />
      <text x="330" y="200" text-anchor="middle" class="cap">Plant</text>
    </svg>

    <p class="text-xs text-white/40 mt-1 text-center">
      Tank level is live; the pump animates while the controller is watering.
    </p>
  </div>
</template>

<style scoped>
.lvl { fill: #fff; font-size: 15px; font-weight: 700; }
.cap { fill: rgba(255, 255, 255, 0.45); font-size: 11px; }
.water-fill { transition: y 0.6s ease, height 0.6s ease; }

/* Flow + pump + active badge only animate while watering */
.flow { opacity: 0; }
.impeller { transform-box: fill-box; transform-origin: center; }
.active-badge { opacity: 0; transition: opacity 0.3s ease; }
.ring { transform-box: fill-box; transform-origin: center; }

.is-watering .flow {
  opacity: 1;
  animation: flow 0.7s linear infinite;
}
.is-watering .impeller {
  animation: spin 1.4s linear infinite;
}
.is-watering .active-badge { opacity: 1; }
.is-watering .ring-a { animation: spin 3s linear infinite; }
.is-watering .ring-b { animation: spin 2s linear infinite reverse; }

@keyframes flow {
  to { stroke-dashoffset: -14; }
}
@keyframes spin {
  to { transform: rotate(360deg); }
}
</style>
