<script setup>
import { ref } from 'vue'
import Button from 'primevue/button'
import { Save } from 'lucide-vue-next'

import AppHeader from './AppHeader.vue'

const LANDING_KEY = 'plantcps_landing'

const landing = ref(localStorage.getItem(LANDING_KEY) || 'welcome')
const saved = ref(false)

function save() {
  localStorage.setItem(LANDING_KEY, landing.value)
  saved.value = true
  setTimeout(() => { saved.value = false }, 2000)
}
</script>

<template>
  <div class="min-h-screen bg-plant-950 relative overflow-hidden">
    <!-- Background blobs -->
    <div class="fixed inset-0 overflow-hidden pointer-events-none">
      <div class="blob w-[400px] h-[400px] bg-plant-800/30 -top-20 -right-20" style="animation-delay: -5s" />
      <div class="blob w-[300px] h-[300px] bg-plant-600/20 bottom-10 -left-20" style="animation-delay: -15s" />
    </div>

    <div class="relative z-10">
      <AppHeader transparent />

      <main class="max-w-2xl mx-auto p-4 sm:p-8 space-y-6">
        <h2 class="text-2xl font-bold text-white">Settings</h2>

        <!-- Landing page preference -->
        <div class="glass rounded-2xl p-5 sm:p-6 space-y-4">
          <div>
            <h3 class="font-semibold text-white mb-1">Default landing page</h3>
            <p class="text-sm text-white/50">Choose which page you see after logging in.</p>
          </div>

          <div class="space-y-2">
            <label
              :class="[
                'flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors',
                landing === 'welcome'
                  ? 'border-plant-500/50 bg-plant-500/15'
                  : 'border-white/10 hover:border-white/20',
              ]"
            >
              <input
                v-model="landing"
                type="radio"
                value="welcome"
                class="accent-plant-500"
              />
              <div>
                <p class="font-medium text-white">Welcome page</p>
                <p class="text-xs text-white/40">Overview with status at a glance</p>
              </div>
            </label>

            <label
              :class="[
                'flex items-center gap-3 p-3 rounded-xl border cursor-pointer transition-colors',
                landing === 'dashboard'
                  ? 'border-plant-500/50 bg-plant-500/15'
                  : 'border-white/10 hover:border-white/20',
              ]"
            >
              <input
                v-model="landing"
                type="radio"
                value="dashboard"
                class="accent-plant-500"
              />
              <div>
                <p class="font-medium text-white">Dashboard</p>
                <p class="text-xs text-white/40">Full sensor data and charts</p>
              </div>
            </label>
          </div>

          <div class="flex items-center gap-3">
            <Button
              @click="save"
              class="!bg-plant-600 !border-plant-600 hover:!bg-plant-500 !rounded-xl"
            >
              <Save class="w-4 h-4 mr-2" />
              Save
            </Button>
            <span v-if="saved" class="text-sm text-plant-400 font-medium">Saved!</span>
          </div>
        </div>
      </main>
    </div>
  </div>
</template>
