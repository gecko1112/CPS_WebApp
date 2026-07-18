<script setup>
import { ref, watch, computed } from 'vue'
import { Leaf, Save } from 'lucide-vue-next'

const props = defineProps({
  // { active, profiles: {name: {moist_lower, moist_upper, dry_days,
  //   suppress_daytime, suppress_rain, rain_suppress_threshold_mm}}, editable }
  // - exact mirror of P05's central-config P05ProfileConfig.
  config: { type: Object, default: null },
  isOperator: { type: Boolean, default: false },
  advanced: { type: Boolean, default: false }, // full param table vs. dropdown
})
const emit = defineEmits(['save'])

const editable = computed(() => Boolean(props.config?.editable) && props.isOperator)
const profileNames = computed(() => Object.keys(props.config?.profiles || {}))

// Only some profiles have editable values (the 'custom' one). Presets are
// fixed. Selecting the active profile works for all of them.
function rowEditable(r) {
  return editable.value && (props.config?.editable_profiles || []).includes(r.name)
}

// Simple view: only switch the active plant, no parameter editing.
function selectActive() {
  emit('save', { active: active.value })
}

const active = ref(null)
const rows = ref([]) // one row per profile, P05ProfileConfig fields
const dirty = ref(false)

// Sync from props - but never clobber an in-progress edit (polling refreshes config).
watch(
  () => props.config,
  (cfg) => {
    if (!cfg || dirty.value) return
    active.value = cfg.active
    rows.value = Object.entries(cfg.profiles || {}).map(([name, d]) => ({
      name,
      moist_lower: d.moist_lower,
      moist_upper: d.moist_upper,
      dry_days: d.dry_days,
      suppress_daytime: d.suppress_daytime,
      suppress_rain: d.suppress_rain,
      rain_suppress_threshold_mm: d.rain_suppress_threshold_mm,
    }))
  },
  { immediate: true },
)

function save() {
  const profiles = {}
  for (const r of rows.value) {
    const lower = Math.min(1, Math.max(0, Number(r.moist_lower)))
    profiles[r.name] = {
      moist_lower: lower,
      // P05 validates upper > lower - enforce it client-side too.
      moist_upper: Math.min(1, Math.max(lower + 0.01, Number(r.moist_upper))),
      dry_days: Math.max(0, Number(r.dry_days)),
      suppress_daytime: Boolean(r.suppress_daytime),
      suppress_rain: Boolean(r.suppress_rain),
      rain_suppress_threshold_mm: Math.max(0, Number(r.rain_suppress_threshold_mm)),
    }
  }
  emit('save', { active: active.value, profiles })
  dirty.value = false
}
</script>

<template>
  <div class="glass rounded-2xl p-4 sm:p-5">
    <div class="flex items-center justify-between gap-2 mb-3">
      <div class="flex items-center gap-2">
        <Leaf class="w-4 h-4 text-plant-400" />
        <h3 class="text-sm font-semibold text-white/60">Plant profiles</h3>
      </div>
      <button
        v-if="advanced && editable && dirty"
        type="button"
        @click="save"
        class="flex items-center gap-1.5 text-xs font-medium px-2.5 py-1 rounded-lg bg-plant-600 text-white hover:bg-plant-500 transition-colors"
      >
        <Save class="w-3.5 h-3.5" /> Save
      </button>
    </div>

    <div v-if="!config || rows.length === 0" class="text-sm text-white/30 py-2">
      No profile information available
    </div>

    <!-- Simple view: just choose the plant -->
    <div v-else-if="!advanced" class="flex items-center gap-3 flex-wrap">
      <span class="text-sm text-white/60">Active plant:</span>
      <select
        v-if="editable"
        v-model="active"
        @change="selectActive"
        class="bg-white/10 border border-white/15 rounded-lg px-3 py-1.5 text-sm text-white capitalize focus:border-plant-500 outline-none"
      >
        <option v-for="p in profileNames" :key="p" :value="p" class="bg-plant-900 text-white">
          {{ p }}
        </option>
      </select>
      <span v-else class="text-sm font-semibold text-white capitalize">
        {{ active || 'Unknown' }}
      </span>
      <span v-if="!editable" class="text-xs text-white/30">
        {{ config && !config.editable ? (config.note || '') : 'Operator role required to change.' }}
      </span>
    </div>

    <!-- Expert view: full editable parameter table -->
    <div v-else class="overflow-x-auto -mx-1 px-1">
      <table class="w-full text-sm border-collapse">
        <thead>
          <tr class="text-left text-xs text-white/40">
            <th class="font-medium py-1 pr-2">Active</th>
            <th class="font-medium py-1 pr-3">Profile</th>
            <th class="font-medium py-1 pr-3">Moisture min</th>
            <th class="font-medium py-1 pr-3">Moisture max</th>
            <th class="font-medium py-1 pr-3">Dry days</th>
            <th class="font-medium py-1 pr-3">Night-only</th>
            <th class="font-medium py-1">Skip rain ≥ mm</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="r in rows"
            :key="r.name"
            class="border-t border-white/5"
            :class="r.name === active ? 'bg-plant-500/10' : ''"
          >
            <td class="py-2 pr-2">
              <input
                type="radio"
                :value="r.name"
                v-model="active"
                :disabled="!editable"
                @change="dirty = true"
                class="accent-plant-500"
              />
            </td>
            <td class="py-2 pr-3 capitalize text-white/80 font-medium">{{ r.name }}</td>
            <td class="py-2 pr-3">
              <input
                v-if="rowEditable(r)"
                type="number"
                step="0.05"
                min="0"
                max="1"
                v-model.number="r.moist_lower"
                @input="dirty = true"
                class="w-16 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none"
              />
              <span v-else class="text-white/70">
                {{ (r.moist_lower * 100).toFixed(0) }}%
              </span>
            </td>
            <td class="py-2 pr-3">
              <input
                v-if="rowEditable(r)"
                type="number"
                step="0.05"
                min="0"
                max="1"
                v-model.number="r.moist_upper"
                @input="dirty = true"
                class="w-16 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none"
              />
              <span v-else class="text-white/70">
                {{ (r.moist_upper * 100).toFixed(0) }}%
              </span>
            </td>
            <td class="py-2 pr-3">
              <input
                v-if="rowEditable(r)"
                type="number"
                min="0"
                v-model.number="r.dry_days"
                @input="dirty = true"
                class="w-14 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none"
              />
              <span v-else class="text-white/70">{{ r.dry_days }}</span>
            </td>
            <td class="py-2 pr-3">
              <input
                type="checkbox"
                v-model="r.suppress_daytime"
                :disabled="!rowEditable(r)"
                @change="dirty = true"
                class="accent-plant-500"
              />
            </td>
            <td class="py-2">
              <div class="flex items-center gap-1.5">
                <input
                  type="checkbox"
                  v-model="r.suppress_rain"
                  :disabled="!rowEditable(r)"
                  @change="dirty = true"
                  class="accent-plant-500"
                />
                <input
                  v-if="rowEditable(r)"
                  type="number"
                  min="0"
                  step="1"
                  v-model.number="r.rain_suppress_threshold_mm"
                  @input="dirty = true"
                  :disabled="!r.suppress_rain"
                  class="w-14 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none disabled:opacity-40"
                />
                <span v-else-if="r.suppress_rain" class="text-white/70">
                  {{ r.rain_suppress_threshold_mm }}
                </span>
              </div>
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="!isOperator" class="text-xs text-white/30 mt-2">
        Operator role required to change profiles.
      </p>
      <p v-else-if="config && config.note" class="text-xs text-white/30 mt-2">
        {{ config.note }}
      </p>
    </div>
  </div>
</template>
