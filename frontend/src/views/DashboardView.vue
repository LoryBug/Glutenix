<script setup>
import { ref, onMounted } from 'vue'
import { listIngredients, listApplications, listBlends, getHealth, getARD } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const healthy = ref(false)
const ingCount = ref(0)
const appCount = ref(0)
const blendCount = ref(0)
const ardImportance = ref(null)
const loading = ref(true)

onMounted(async () => {
  try {
    healthy.value = await getHealth().then(() => true).catch(() => false)
    const [ings, apps, blends] = await Promise.all([
      listIngredients().catch(() => []),
      listApplications().catch(() => []),
      listBlends().catch(() => []),
    ])
    ingCount.value = ings.length
    appCount.value = apps.length
    blendCount.value = blends.length
    ardImportance.value = await getARD().catch(() => null)
  } finally { loading.value = false }
})
</script>

<template>
  <div>
    <h1 style="margin-bottom:.25rem;">Dashboard</h1>
    <p class="text-sm text-xs" style="margin-bottom:1.25rem;">Panoramica del sistema Glutenix</p>

    <HelpBox title="Aiuto: dashboard e modello predittivo">
      <p>Questa pagina riassume lo stato del sistema: ingredienti disponibili, applicazioni, blend creati e connessione con l'API.</p>
      <p>Quando il modello GPR e addestrato, la sezione ARD mostra quali feature del blend influenzano di piu la predizione del volume. Il modello restituisce una media prevista e una stima di incertezza: valori ARD alti indicano variabili piu rilevanti per la predizione.</p>
    </HelpBox>

    <div v-if="loading" class="text-center text-sm" style="padding:2rem;">Caricamento...</div>

    <template v-else>
      <div class="grid-3">
        <div class="card text-center">
          <div style="font-size:2rem;font-weight:700;color:#16a34a;">{{ ingCount }}</div>
          <div class="text-xs">Ingredienti</div>
        </div>
        <div class="card text-center">
          <div style="font-size:2rem;font-weight:700;color:#2563eb;">{{ appCount }}</div>
          <div class="text-xs">Applicazioni</div>
        </div>
        <div class="card text-center">
          <div style="font-size:2rem;font-weight:700;color:#d97706;">{{ blendCount }}</div>
          <div class="text-xs">Blend creati</div>
        </div>
      </div>

      <div class="card mt-2" v-if="healthy">
        <h2 style="font-size:1rem;margin-bottom:.5rem;">Stato API</h2>
        <span class="badge db" style="background:#dcfce7;color:#166534;">✅ Server online</span>
      </div>

      <div class="card mt-2" v-if="ardImportance">
        <h2 style="font-size:1rem;margin-bottom:.5rem;">Feature importance (ARD)</h2>
        <table>
          <tr><th>Feature</th><th>Importanza</th></tr>
          <tr v-for="(v, k) in ardImportance.importance" :key="k">
            <td>{{ k }}</td><td>{{ v.toFixed(4) }}</td>
          </tr>
        </table>
      </div>
    </template>
  </div>
</template>
