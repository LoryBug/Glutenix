<script setup>
import { ref, computed, onMounted, watch } from 'vue'
import { useRouter } from 'vue-router'
import { listBlends, simulate } from '../api/client'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import HelpBox from '../components/HelpBox.vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const router = useRouter()
const blends = ref([])
const loading = ref(true)
const running = ref(false)
const result = ref(null)
const error = ref('')

const simForm = ref({
  blend_id: null,
  fermentation_temp_c: 30,
  fermentation_duration_min: 120,
  baking_temp_c: 200,
  baking_duration_min: 25,
})

onMounted(async () => {
  blends.value = await listBlends().catch(() => [])
  loading.value = false
  if (blends.value.length) simForm.value.blend_id = blends.value[0].id
})

async function run() {
  error.value = ''
  result.value = null
  running.value = true
  try {
    result.value = await simulate(simForm.value)
  } catch (e) { error.value = e.response?.data?.detail || e.message }
  finally { running.value = false }
}

const chartData = computed(() => {
  if (!result.value) return null
  const r = result.value
  return {
    labels: ['Fermentazione\n+Volume', 'Cottura\nCore °C', 'Cottura\nCrosta °C'],
    datasets: [{
      label: 'Risultati simulazione',
      data: [
        (r.fermentation_volume_increase * 100).toFixed(1),
        r.baking_core_temp_c,
        r.baking_crust_temp_c,
      ],
      backgroundColor: ['#16a34a', '#d97706', '#dc2626'],
      borderRadius: 6,
    }]
  }
})

const chartOptions = {
  responsive: true,
  plugins: { legend: { display: false }, tooltip: { callbacks: { label: (ctx) => ctx.parsed.y } } },
  scales: {
    y: { beginAtZero: true, grid: { color: '#f0f0f0' } },
    x: { grid: { display: false } },
  },
}
</script>

<template>
  <div>
    <div class="flex" style="justify-content:space-between;margin-bottom:1rem;">
      <h1>Simulazione</h1>
      <button class="btn-outline" @click="router.push('/simulate/history')">📜 Storico</button>
    </div>

    <HelpBox title="Aiuto: simulazione e predizione">
      <p>Questa pagina esegue la simulazione fisica del blend: fermentazione per stimare l'aumento di volume e cottura per stimare temperatura al cuore, crosta e gelatinizzazione.</p>
      <p>La simulazione non e il modello GPR: e il motore fisico. Il GPR impara da dati simulati o sperimentali e predice rapidamente il risultato atteso, aggiungendo incertezza quando le feature sono lontane dai dati conosciuti.</p>
    </HelpBox>

    <div class="card mb-2">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Parametri</h2>
      <div class="grid-2">
        <div>
          <label class="text-xs">Blend</label>
          <select v-model="simForm.blend_id">
            <option v-for="b in blends" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div><label class="text-xs">Temp. fermentazione (°C)</label><input v-model.number="simForm.fermentation_temp_c" type="number"></div>
        <div><label class="text-xs">Durata fermentazione (min)</label><input v-model.number="simForm.fermentation_duration_min" type="number"></div>
        <div><label class="text-xs">Temp. forno (°C)</label><input v-model.number="simForm.baking_temp_c" type="number"></div>
        <div><label class="text-xs">Durata cottura (min)</label><input v-model.number="simForm.baking_duration_min" type="number"></div>
      </div>
      <p v-if="error" style="color:#dc2626;font-size:.85rem;margin-top:.5rem;">{{ error }}</p>
      <button class="mt-1" @click="run" :disabled="running || !simForm.blend_id">
        {{ running ? '⏳ Simulando...' : '▶ Avvia simulazione' }}
      </button>
    </div>

    <div v-if="result" class="card">
      <div style="display:grid;grid-template-columns: 1fr 1fr;gap:1.5rem;">
        <div>
          <h2 style="font-size:.95rem;margin-bottom:.5rem;">Riepilogo</h2>
          <table>
            <tr><td>Proteine</td><td>{{ result.protein_pct.toFixed(2) }}%</td></tr>
            <tr><td>Amido</td><td>{{ result.starch_pct.toFixed(2) }}%</td></tr>
            <tr><td>Viscosità</td><td>{{ result.viscosity_index.toFixed(2) }}</td></tr>
            <tr><td>Gelatinizzazione</td><td>{{ result.gelatinization_temp_min.toFixed(1) }}°C — {{ result.gelatinization_temp_max.toFixed(1) }}°C</td></tr>
            <tr><td style="font-weight:600;color:#16a34a;">+ Volume</td><td><strong>{{ (result.fermentation_volume_increase * 100).toFixed(1) }}%</strong></td></tr>
            <tr><td style="font-weight:600;color:#d97706;">Core temp</td><td><strong>{{ result.baking_core_temp_c.toFixed(1) }}°C</strong></td></tr>
            <tr><td style="font-weight:600;color:#dc2626;">Crosta temp</td><td><strong>{{ result.baking_crust_temp_c.toFixed(1) }}°C</strong></td></tr>
          </table>
        </div>
        <div v-if="chartData">
          <h2 style="font-size:.95rem;margin-bottom:.5rem;">Risultati</h2>
          <Bar :data="chartData" :options="chartOptions" />
        </div>
      </div>

      <div style="margin-top:.75rem;padding:.5rem;background:#f0fdf4;border-radius:8px;font-size:.85rem;">
        <strong>💡 Interpretazione:</strong>
        <span v-if="result.baking_core_temp_c < result.gelatinization_temp_min">
          Il core ({{ result.baking_core_temp_c.toFixed(1) }}°C) non raggiunge la gelatinizzazione ({{ result.gelatinization_temp_min.toFixed(1) }}°C). Prova ad aumentare tempo o temperatura di cottura.
        </span>
        <span v-else>
          Il core supera la gelatinizzazione — buona struttura della mollica attesa.
        </span>
      </div>
    </div>
  </div>
</template>
