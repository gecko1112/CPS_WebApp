// In-app toast store. pushToast() from anywhere; <ToastHost> renders them.
import { ref } from 'vue'

export const toasts = ref([])
let nextId = 1

export function pushToast({ title = '', message = '', severity = 'info', timeout = 6000 } = {}) {
  const id = nextId++
  toasts.value.push({ id, title, message, severity })
  if (timeout) setTimeout(() => dismissToast(id), timeout)
  return id
}

export function dismissToast(id) {
  toasts.value = toasts.value.filter((t) => t.id !== id)
}
