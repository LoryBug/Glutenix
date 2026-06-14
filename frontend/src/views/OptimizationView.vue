<script setup>
import { ref, onMounted } from 'vue'
import { getARD } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const importance = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    const data = await getARD()
    importance.value = data.importance
  } catch { }
  finally { loading.value = false }
})

function maxVal() {
  if (!importance.value) return 1
  return Math.max(...Object.values(importance.value), 0.001)
}
</script>

<template>
  <div>
    <h1 style="margin-bottom:.5rem;">Ottimizzazione</h1>
    <p class="text-sm text-xs mb-2">Importanza delle feature calcolata con ARD (Automatic Relevance Determination).</p>

    <HelpBox title="Aiuto: ottimizzazione e ARD">
      <p>Questa pagina mostra quali feature pesano di piu nella predizione del modello. ARD assegna una rilevanza alle feature: valori piu alti indicano variabili che il GPR usa maggiormente per spiegare il risultato.</p>
      <p>In pratica, ARD aiuta a capire dove intervenire: proteine, amido, fibre, idrocolloidi, gelatinizzazione o viscosita. L'ottimizzazione usa queste informazioni insieme a simulazioni e vincoli per proporre blend piu promettenti.</p>
    </HelpBox>

    <div class="card" v-if="!loading && importance">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Feature importance</h2>
      <p class="text-xs mb-1">Più alto = più impatto sulla predizione del volume.</p>
      <div v-for="(v, k) in importance" :key="k" class="flex mb-1">
        <span style="width:160px;font-size:.85rem;">{{ k }}</span>
        <div style="flex:1;background:#e5e7eb;border-radius:4px;height:18px;overflow:hidden;">
          <div :style="{ width: (v / maxVal() * 100) + '%', background: '#2563eb', height: '100%', borderRadius: '4px' }"></div>
        </div>
        <span style="width:50px;text-align:right;font-size:.8rem;">{{ v.toFixed(3) }}</span>
      </div>
    </div>
    <div v-else-if="!loading && !importance" class="card">
      <p class="text-sm text-xs">Modello non addestrato. Addestra il GPR per vedere le feature importance.</p>
    </div>
  </div>
</template>
