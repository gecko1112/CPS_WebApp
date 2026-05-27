<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'
import { Sprout } from 'lucide-vue-next'
import { login } from '../composables/useApi'
import router from '../router'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
    const preferred = localStorage.getItem('plantcps_landing') || 'welcome'
    router.push({ name: preferred })
  } catch (e) {
    error.value = 'Login failed. Check username and password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4 bg-plant-950">
    <!-- Background blobs -->
    <div class="absolute inset-0 overflow-hidden">
      <div class="blob w-[500px] h-[500px] bg-plant-700/30 -top-32 -right-32" style="animation-delay: 0s" />
      <div class="blob w-[400px] h-[400px] bg-plant-500/20 bottom-0 -left-32" style="animation-delay: -10s" />
    </div>

    <div class="relative w-full max-w-sm glass rounded-2xl p-6 sm:p-8">
      <div class="flex items-center gap-3 mb-6">
        <div class="bg-plant-600 p-2 rounded-xl">
          <Sprout class="w-6 h-6 text-white" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-white">Plant CPS</h1>
          <p class="text-sm text-white/50">Sign in to view your plants</p>
        </div>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-white/70 mb-1">Username</label>
          <InputText v-model="username" class="w-full" autocomplete="username" />
        </div>
        <div>
          <label class="block text-sm font-medium text-white/70 mb-1">Password</label>
          <Password
            v-model="password"
            :feedback="false"
            toggle-mask
            class="w-full"
            input-class="w-full"
            autocomplete="current-password"
          />
        </div>

        <Message v-if="error" severity="error" :closable="false">{{ error }}</Message>

        <Button
          type="submit"
          label="Sign in"
          :loading="loading"
          class="w-full !bg-plant-600 !border-plant-600 hover:!bg-plant-500 !rounded-xl"
        />
      </form>

      <div class="mt-6 pt-4 border-t border-white/10 text-xs text-white/40">
        <p class="font-semibold mb-1 text-white/60">Test accounts:</p>
        <p>viewer / viewer123 — read only</p>
        <p>operator / operator123 — can water</p>
      </div>
    </div>
  </div>
</template>
