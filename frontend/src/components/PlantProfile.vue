<script setup>
import { ref, watch, computed } from 'vue'
import { Leaf, Save } from 'lucide-vue-next'

const props = defineProps({
  // { active, profiles: {name: {target_moist, dry_days, suppress_daytime}}, editable }
  config: { type: Object, default: null },
  isOperator: { type: Boolean, default: false },
  advanced: { type: Boolean, default: false }, // full param table vs. dropdown
})
const emit = defineEmits(['save'])

const editable = computed(() => Boolean(props.config?.editable) && props.isOperator)
const profileNames = computed(() => Object.keys(props.config?.profiles || {}))

// Simple view: only switch the active plant, no parameter editing.
function selectActive() {
  emit('save', { active: active.value })
}

const active = ref(null)
const rows = ref([]) // [{ name, target_moist, dry_days, suppress_daytime }]
const dirty = ref(false)

// Sync from props — but never clobber an in-progress edit (polling refreshes config).
watch(
  () => props.config,
  (cfg) => {
    if (!cfg || dirty.value) return
    active.value = cfg.active
    rows.value = Object.entries(cfg.profiles || {}).map(([name, d]) => ({
      name,
      target_moist: d.target_moist,
      dry_days: d.dry_days,
      suppress_daytime: d.suppress_daytime,
    }))
  },
  { immediate: true },
)

function save() {
  const profiles = {}
  for (const r of rows.value) {
    profiles[r.name] = {
      target_moist: Math.min(1, Math.max(0, Number(r.target_moist))),
      dry_days: Math.max(0, Number(r.dry_days)),
      suppress_daytime: Boolean(r.suppress_daytime),
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
            <th class="font-medium py-1 pr-3">Target moisture</th>
            <th class="font-medium py-1 pr-3">Dry days</th>
            <th class="font-medium py-1">Night-only</th>
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
              <template v-if="editable">
                <input
                  type="number"
                  step="0.05"
                  min="0"
                  max="1"
                  v-model.number="r.target_moist"
                  @input="dirty = true"
                  class="w-16 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none"
                />
              </template>
              <span v-else class="text-white/70">
                {{ (r.target_moist * 100).toFixed(0) }}%
              </span>
            </td>
            <td class="py-2 pr-3">
              <input
                v-if="editable"
                type="number"
                min="0"
                v-model.number="r.dry_days"
                @input="dirty = true"
                class="w-14 bg-white/5 rounded px-1.5 py-0.5 text-white/90 border border-white/10 focus:border-plant-500 outline-none"
              />
              <span v-else class="text-white/70">{{ r.dry_days }}</span>
            </td>
            <td class="py-2">
              <input
                type="checkbox"
                v-model="r.suppress_daytime"
                :disabled="!editable"
                @change="dirty = true"
                class="accent-plant-500"
              />
            </td>
          </tr>
        </tbody>
      </table>

      <p v-if="config && !config.editable" class="text-xs text-white/30 mt-2">
        {{ config.note || 'Profiles are read-only in this mode.' }}
      </p>
      <p v-else-if="!isOperator" class="text-xs text-white/30 mt-2">
        Operator role required to edit profiles.
      </p>
    </div>
  </div>
</template>
