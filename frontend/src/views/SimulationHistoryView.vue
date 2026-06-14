<script setup>
import { ref, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listSimulations, listBlends } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const router = useRouter()
const simulations = ref([])
const blends = ref({})
const loading = ref(true)

onMounted(async () => {
  try {
    const [sims, bls] = await Promise.all([
      listSimulations().catch(() => []),
      listBlends().catch(() => []),
    ])
    for (const b of bls) blends.value[b.id] = b.name
    simulations.value = sims
  } finally { loading.value = false }
})

function parseResult(sim) {
  try { return JSON.parse(sim.results) } catch { return null }
}
</script>

<template>
  <div>
    <div class="flex" style="justify-content:space-between;margin-bottom:1rem;">
      <h1>Storico simulazioni</h1>
      <button class="btn-outline" @click="router.push('/simulate')">← Nuova simulazione</button>
    </div>

    <HelpBox title="Aiuto: storico e interpretazione risultati">
      <p>Qui trovi le simulazioni salvate, con blend, incremento di volume, temperatura al cuore, temperatura della crosta e data di esecuzione.</p>
      <p>Lo storico serve per confrontare configurazioni diverse. Questi risultati possono diventare dataset di calibrazione per il modello GPR, che usa esempi passati per predire nuovi blend e indicare quanto e sicuro della previsione.</p>
    </HelpBox>

    <div v-if="loading" class="text-center text-sm" style="padding:2rem;">Caricamento...</div>

    <div v-else-if="!simulations.length" class="card text-center text-sm" style="padding:2rem;color:#888;">
      Nessuna simulazione ancora eseguita.
    </div>

    <div v-else class="card">
      <table>
        <tr><th>ID</th><th>Blend</th><th>+Volume</th><th>Core °C</th><th>Crosta °C</th><th>Data</th></tr>
        <tr v-for="sim in simulations" :key="sim.id">
          <td>{{ sim.id }}</td>
          <td>{{ blends[sim.blend_id] || '?' }}</td>
          <td v-if="parseResult(sim)">
            <span class="badge" :class="parseResult(sim).fermentation_volume_increase * 100 > 50 ? 'db' : 'engine'">
              {{ (parseResult(sim).fermentation_volume_increase * 100).toFixed(1) }}%
            </span>
          </td>
          <td v-else>-</td>
          <td v-if="parseResult(sim)">{{ parseResult(sim).baking_core_temp_c.toFixed(1) }}°C</td>
          <td v-else>-</td>
          <td v-if="parseResult(sim)">{{ parseResult(sim).baking_crust_temp_c.toFixed(1) }}°C</td>
          <td v-else>-</td>
          <td class="text-xs">{{ sim.created_at?.slice(0, 16).replace('T', ' ') }}</td>
        </tr>
      </table>
    </div>
  </div>
</template>
