<script setup>
import { ref, computed, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { listApplications, listBlends, simulateSweep } from '../api/client'
import { Bar } from 'vue-chartjs'
import { Chart as ChartJS, CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend } from 'chart.js'
import HelpBox from '../components/HelpBox.vue'

ChartJS.register(CategoryScale, LinearScale, BarElement, Title, Tooltip, Legend)

const router = useRouter()
const blends = ref([])
const applications = ref([])
const loading = ref(true)
const running = ref(false)
const result = ref(null)
const error = ref('')

const form = ref({
  blend_id: null,
  application_id: null,
  strategy: 'random',
  n_samples: 200,
  top_n: 10,
  seed: null,
  fermentation_temp: { min: 25, max: 35, step: 2.5 },
  fermentation_duration: { min: 60, max: 180, step: 20 },
  baking_temp: { min: 180, max: 220, step: 10 },
  baking_duration: { min: 15, max: 35, step: 5 },
  w_volume: 0.30,
  w_gelatinization: 0.40,
  w_crust: 0.20,
  w_efficiency: 0.10,
})

onMounted(async () => {
  const [loadedBlends, loadedApplications] = await Promise.all([
    listBlends().catch(() => []),
    listApplications().catch(() => []),
  ])
  blends.value = loadedBlends
  applications.value = loadedApplications
  loading.value = false
  if (blends.value.length) form.value.blend_id = blends.value[0].id
})

async function run() {
  error.value = ''
  result.value = null
  running.value = true
  try {
    result.value = await simulateSweep(form.value)
  } catch (e) { error.value = e.response?.data?.detail || e.message }
  finally { running.value = false }
}

const topScores = computed(() => {
  if (!result.value?.points?.length) return []
  return result.value.points.slice(0, 10)
})

const chartData = computed(() => {
  const pts = topScores.value
  if (!pts.length) return null
  return {
    labels: pts.map((_, i) => `#${i + 1}`),
    datasets: [
      {
        label: 'Volume Increase %',
        data: pts.map(p => +(p.volume_increase * 100).toFixed(1)),
        backgroundColor: '#16a34a',
        borderRadius: 4,
      },
      {
        label: 'Core °C',
        data: pts.map(p => p.core_temp_c),
        backgroundColor: '#d97706',
        borderRadius: 4,
      },
      {
        label: 'Score',
        data: pts.map(p => +(p.composite_score * 100).toFixed(1)),
        backgroundColor: '#6366f1',
        borderRadius: 4,
      },
    ],
  }
})

const chartOptions = {
  responsive: true,
  plugins: {
    legend: { position: 'top' },
    tooltip: { callbacks: { label: (ctx) => `${ctx.dataset.label}: ${ctx.parsed.y}` } },
  },
  scales: {
    y: { beginAtZero: true, grid: { color: '#f0f0f0' } },
    x: { grid: { display: false } },
  },
}
</script>

<template>
  <div>
    <div class="flex" style="justify-content:space-between;margin-bottom:1rem;">
      <h1>Sweep Simulazioni</h1>
      <button class="btn-outline" @click="router.push('/simulate')">← Singola</button>
    </div>

    <HelpBox title="Aiuto: sweep parametrico">
      <p>Esegue centinaia di simulazioni variando automaticamente temperatura e durata di fermentazione e cottura, per trovare la combinazione ottimale per il blend scelto.</p>
      <p><strong>Strategia:</strong> <em>grid</em> esplora tutte le combinazioni con lo step indicato; <em>random</em> campiona casualmente <code>n_samples</code> punti. I risultati sono ordinati per <em>composite score</em>, una media pesata di volume, temperatura al cuore, crosta ed efficienza tempo.</p>
    </HelpBox>

    <div class="card mb-2">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Parametri sweep</h2>
      <div class="grid-3">
        <div>
          <label class="text-xs">Blend</label>
          <select v-model="form.blend_id">
            <option v-for="b in blends" :key="b.id" :value="b.id">{{ b.name }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs">Profilo applicazione</label>
          <select v-model="form.application_id">
            <option :value="null">Auto / generico</option>
            <option v-for="a in applications" :key="a.id" :value="a.id">{{ a.name }}</option>
          </select>
        </div>
        <div>
          <label class="text-xs">Strategia</label>
          <select v-model="form.strategy">
            <option value="grid">Grid</option>
            <option value="random">Random</option>
          </select>
        </div>
        <div>
          <label class="text-xs">Top N</label>
          <input v-model.number="form.top_n" type="number" min="1" max="100">
        </div>
        <div v-if="form.strategy === 'random'">
          <label class="text-xs">n_samples</label>
          <input v-model.number="form.n_samples" type="number" min="10" max="10000">
        </div>
        <div v-if="form.strategy === 'random'">
          <label class="text-xs">Seed (opzionale)</label>
          <input v-model.number="form.seed" type="number" placeholder="nessuno">
        </div>
      </div>

      <details style="margin-top:.75rem;">
        <summary style="cursor:pointer;font-size:.85rem;color:#666;">Range parametri</summary>
        <div class="grid-4 mt-1">
          <div><label class="text-xs">Fermentaz. T min</label><input v-model.number="form.fermentation_temp.min" type="number" step="0.5"></div>
          <div><label class="text-xs">Fermentaz. T max</label><input v-model.number="form.fermentation_temp.max" type="number" step="0.5"></div>
          <div><label class="text-xs">Fermentaz. T step</label><input v-model.number="form.fermentation_temp.step" type="number" step="0.5"></div>
          <div><label class="text-xs">Fermentaz. durata min</label><input v-model.number="form.fermentation_duration.min" type="number"></div>
          <div><label class="text-xs">Fermentaz. durata max</label><input v-model.number="form.fermentation_duration.max" type="number"></div>
          <div><label class="text-xs">Fermentaz. durata step</label><input v-model.number="form.fermentation_duration.step" type="number"></div>
          <div><label class="text-xs">Cottura T min</label><input v-model.number="form.baking_temp.min" type="number"></div>
          <div><label class="text-xs">Cottura T max</label><input v-model.number="form.baking_temp.max" type="number"></div>
          <div><label class="text-xs">Cottura T step</label><input v-model.number="form.baking_temp.step" type="number"></div>
          <div><label class="text-xs">Cottura durata min</label><input v-model.number="form.baking_duration.min" type="number"></div>
          <div><label class="text-xs">Cottura durata max</label><input v-model.number="form.baking_duration.max" type="number"></div>
          <div><label class="text-xs">Cottura durata step</label><input v-model.number="form.baking_duration.step" type="number"></div>
        </div>
      </details>

      <details style="margin-top:.5rem;">
        <summary style="cursor:pointer;font-size:.85rem;color:#666;">Pesi score composito</summary>
        <div class="grid-4 mt-1">
          <div><label class="text-xs">Peso volume</label><input v-model.number="form.w_volume" type="number" min="0" max="1" step="0.05"></div>
          <div><label class="text-xs">Peso core</label><input v-model.number="form.w_gelatinization" type="number" min="0" max="1" step="0.05"></div>
          <div><label class="text-xs">Peso crosta</label><input v-model.number="form.w_crust" type="number" min="0" max="1" step="0.05"></div>
          <div><label class="text-xs">Peso efficienza</label><input v-model.number="form.w_efficiency" type="number" min="0" max="1" step="0.05"></div>
        </div>
      </details>

      <p v-if="error" style="color:#dc2626;font-size:.85rem;margin-top:.5rem;">{{ error }}</p>
      <button class="mt-1" @click="run" :disabled="running || !form.blend_id">
        {{ running ? '⏳ Sweep in corso...' : '▶ Avvia sweep' }}
      </button>
    </div>

    <div v-if="result" class="card">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">
        Risultati — {{ result.points.length }} migliori su {{ result.n_total }} simulazioni
      </h2>
      <p style="font-size:.85rem;color:#666;margin-bottom:.75rem;">Profilo target: <strong>{{ result.target_profile }}</strong></p>

      <div v-if="chartData" style="max-width:600px;margin-bottom:1rem;">
        <Bar :data="chartData" :options="chartOptions" />
      </div>

      <table>
        <thead>
          <tr>
            <th>#</th>
            <th>Fermentaz.<br>°C</th>
            <th>Fermentaz.<br>min</th>
            <th>Cottura<br>°C</th>
            <th>Cottura<br>min</th>
            <th>+Volume</th>
            <th>Core °C</th>
            <th>Crosta °C</th>
            <th>Score</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="(p, i) in topScores" :key="i">
            <td>{{ i + 1 }}</td>
            <td>{{ p.fermentation_temp_c }}</td>
            <td>{{ p.fermentation_duration_min }}</td>
            <td>{{ p.baking_temp_c }}</td>
            <td>{{ p.baking_duration_min }}</td>
            <td style="color:#16a34a;font-weight:600;">{{ (p.volume_increase * 100).toFixed(1) }}%</td>
            <td style="color:#d97706;">{{ p.core_temp_c }}°C</td>
            <td style="color:#dc2626;">{{ p.crust_temp_c }}°C</td>
            <td style="font-weight:700;">{{ (p.composite_score * 100).toFixed(1) }}</td>
          </tr>
        </tbody>
      </table>

      <div v-if="result.points.length" style="margin-top:.75rem;padding:.5rem;background:#f0fdf4;border-radius:8px;font-size:.85rem;">
        <strong>💡 Miglior combo:</strong>
        Fermentazione a <strong>{{ result.points[0].fermentation_temp_c }}°C</strong> per <strong>{{ result.points[0].fermentation_duration_min }} min</strong>,
        cottura a <strong>{{ result.points[0].baking_temp_c }}°C</strong> per <strong>{{ result.points[0].baking_duration_min }} min</strong>.
        Volume +{{ (result.points[0].volume_increase * 100).toFixed(1) }}%, core {{ result.points[0].core_temp_c }}°C.
      </div>
    </div>
  </div>
</template>
