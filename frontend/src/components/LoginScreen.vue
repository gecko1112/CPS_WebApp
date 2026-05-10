<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import InputText from 'primevue/inputtext'
import Password from 'primevue/password'
import Message from 'primevue/message'
import { Sprout } from 'lucide-vue-next'
import { login } from '../composables/useApi'

const username = ref('')
const password = ref('')
const error = ref('')
const loading = ref(false)

async function submit() {
  error.value = ''
  loading.value = true
  try {
    await login(username.value, password.value)
  } catch (e) {
    error.value = 'Login failed. Check username and password.'
  } finally {
    loading.value = false
  }
}
</script>

<template>
  <div class="min-h-screen flex items-center justify-center p-4">
    <div class="w-full max-w-sm bg-white rounded-2xl shadow-lg p-6 sm:p-8">
      <div class="flex items-center gap-3 mb-6">
        <div class="bg-emerald-100 p-2 rounded-xl">
          <Sprout class="w-6 h-6 text-emerald-600" />
        </div>
        <div>
          <h1 class="text-xl font-bold text-slate-900">Plant CPS</h1>
          <p class="text-sm text-slate-500">Sign in to view your plants</p>
        </div>
      </div>

      <form @submit.prevent="submit" class="space-y-4">
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Username</label>
          <InputText v-model="username" class="w-full" autocomplete="username" />
        </div>
        <div>
          <label class="block text-sm font-medium text-slate-700 mb-1">Password</label>
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

        <Button type="submit" label="Sign in" :loading="loading" class="w-full" />
      </form>

      <div class="mt-6 pt-4 border-t border-slate-200 text-xs text-slate-500">
        <p class="font-semibold mb-1">Test accounts:</p>
        <p>viewer / viewer123 — read only</p>
        <p>operator / operator123 — can water</p>
      </div>
    </div>
  </div>
</template>
