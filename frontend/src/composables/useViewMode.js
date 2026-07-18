// Simple vs. advanced view preference (a UI choice, separate from role).
// 'simple'   - non-expert: friendly cards, plain language, no raw values.
// 'advanced' - CPS-aware: adds raw readings, controller detail, history, etc.
// Deliberately not persisted, so the app always opens in the simple view (the
// non-expert default). Advanced is an opt-in per session.
import { ref } from 'vue'

export const viewMode = ref('simple')

export function setViewMode(mode) {
  viewMode.value = mode === 'advanced' ? 'advanced' : 'simple'
}

export function toggleViewMode() {
  setViewMode(viewMode.value === 'simple' ? 'advanced' : 'simple')
}
