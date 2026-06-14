<script setup>
import { ref } from 'vue'
import { predict } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const features = ref([5, 70, 2, 3, 1.5, 65, 20, 1.5, 0.02])
const result = ref(null)
const error = ref('')
const loading = ref(false)

const labels = ['Proteine %', 'Amido %', 'Grassi %', 'Fibre %', 'Assorb. acqua', 'Gelat. min °C', 'Amilosio %', 'Viscosità', 'Idrocolloidi %']

async function run() {
  error.value = ''
  result.value = null
  loading.value = true
  try {
    result.value = await predict({ features: features.value.map(Number) })
  } catch (e) { error.value = e.response?.data?.detail || e.message }
  finally { loading.value = false }
}
</script>

<template>
  <div>
    <h1 style="margin-bottom:1rem;">Predizione GPR</h1>
    <p class="text-sm text-xs mb-2">Inserisci le feature del blend per predire l'incremento di volume con il modello GPR.</p>

    <HelpBox title="Aiuto: modello di predizione GPR">
      <p>Questa pagina interroga direttamente il modello Gaussian Process Regression. Inserisci le feature numeriche del blend e il modello restituisce la media prevista dell'obiettivo, la deviazione standard e un intervallo di confidenza al 95%.</p>
      <p>La deviazione standard misura l'incertezza: se e alta, il blend assomiglia poco ai dati usati per addestrare il modello o la relazione e poco chiara. Il modello non sostituisce la simulazione o il test reale, ma aiuta a filtrare rapidamente le formule piu promettenti.</p>
    </HelpBox>

    <div class="card mb-2">
      <div class="grid-2">
        <div v-for="(label, i) in labels" :key="i">
          <label class="text-xs">{{ label }}</label>
          <input v-model.number="features[i]" type="number" step="0.1">
        </div>
      </div>
      <button class="mt-1" @click="run" :disabled="loading">{{ loading ? 'Predicendo...' : 'Predici' }}</button>
    </div>

    <div v-if="error" class="card" style="background:#fef2f2;">
      <p style="color:#dc2626;">{{ error }}</p>
    </div>

    <div v-if="result" class="card">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Risultato</h2>
      <table>
        <tr><td>Media predetta</td><td><strong>{{ result.mean.toFixed(4) }}</strong></td></tr>
        <tr><td>Deviazione std</td><td>{{ result.std.toFixed(4) }}</td></tr>
        <tr><td>Intervallo 95%</td><td>[{{ result.conf_interval_95[0] }}, {{ result.conf_interval_95[1] }}]</td></tr>
      </table>
      <p class="text-xs mt-1">Più alto è lo std, meno il modello è sicuro (es. feature fuori distribuzione).</p>
    </div>
  </div>
</template>
