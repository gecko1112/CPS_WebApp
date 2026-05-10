<script setup>
import { computed } from 'vue'
import { authState } from './composables/useApi'
import LoginScreen from './components/LoginScreen.vue'
import Dashboard from './components/Dashboard.vue'

const isLoggedIn = computed(() => Boolean(authState.value.token))
</script>

<template>
  <Dashboard v-if="isLoggedIn" />
  <LoginScreen v-else />
</template>
