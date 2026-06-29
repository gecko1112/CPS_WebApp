// Simple vs. advanced view preference (a UI choice, separate from role).
// 'simple'   — non-expert: friendly cards, plain language, no raw values.
// 'advanced' — CPS-aware: adds raw readings, controller detail, history, etc.
import { ref } from 'vue'

const KEY = 'plantcps_viewmode'

export const viewMode = ref(localStorage.getItem(KEY) || 'simple')

export function setViewMode(mode) {
  viewMode.value = mode === 'advanced' ? 'advanced' : 'simple'
  localStorage.setItem(KEY, viewMode.value)
}

export function toggleViewMode() {
  setViewMode(viewMode.value === 'simple' ? 'advanced' : 'simple')
}
