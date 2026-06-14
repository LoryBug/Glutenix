<script setup>
import { ref, onMounted } from 'vue'
import { listIngredients, listBlends, createBlend, deleteBlend } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const ingredients = ref([])
const blends = ref([])
const loading = ref(true)
const showForm = ref(false)
const form = ref({ name: '', ingredients: [{ ingredient_id: 1, proportion: 1 }] })
const error = ref('')

async function load() {
  loading.value = true
  const [ings, bls] = await Promise.all([
    listIngredients().catch(() => []),
    listBlends().catch(() => [])
  ])
  ingredients.value = ings
  blends.value = bls
  loading.value = false
}

onMounted(load)

function addRow() { form.value.ingredients.push({ ingredient_id: ingredients.value[0]?.id || 1, proportion: 0 }) }
function removeRow(i) { form.value.ingredients.splice(i, 1) }

async function submit() {
  error.value = ''
  const total = form.value.ingredients.reduce((s, r) => s + r.proportion, 0)
  if (Math.abs(total - 1) > 0.01) { error.value = `Le proporzioni devono sumare a 1 (attuale: ${total.toFixed(2)})`; return }
  try {
    await createBlend({ name: form.value.name, ingredients: form.value.ingredients })
    form.value = { name: '', ingredients: [{ ingredient_id: ingredients.value[0]?.id || 1, proportion: 1 }] }
    showForm.value = false
    await load()
  } catch (e) { error.value = e.response?.data?.detail || e.message }
}

async function remove(id) {
  if (!confirm('Eliminare questo blend?')) return
  try {
    await deleteBlend(id)
    await load()
  } catch (e) { alert(e.response?.data?.detail || e.message) }
}
</script>

<template>
  <div>
    <div class="flex" style="justify-content:space-between;margin-bottom:1rem;">
      <h1>Blend</h1>
      <button @click="showForm = !showForm">{{ showForm ? 'Annulla' : '+ Nuovo blend' }}</button>
    </div>

    <HelpBox title="Aiuto: blend e modello predittivo">
      <p>In questa pagina crei miscele con proporzioni normalizzate: la somma degli ingredienti deve essere 1.0, cioe 100% del blend.</p>
      <p>Il blend viene trasformato in feature fisico-chimiche aggregate. Queste feature alimentano la simulazione e, quando disponibile, il modello GPR che predice l'incremento di volume con una stima dell'incertezza.</p>
    </HelpBox>

    <div v-if="showForm" class="card mb-2">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Nuovo blend</h2>
      <div class="mb-1"><label class="text-xs">Nome blend</label><input v-model="form.name" placeholder="es. Miscela pane"></div>
      <div v-for="(row, i) in form.ingredients" :key="i" class="flex mb-1">
        <select v-model="row.ingredient_id" style="flex:2">
          <option v-for="ing in ingredients" :key="ing.id" :value="ing.id">{{ ing.name }}</option>
        </select>
        <input v-model.number="row.proportion" type="number" step="0.05" min="0" max="1" style="flex:1" placeholder="%">
        <button class="btn-danger btn-sm" @click="removeRow(i)" v-if="form.ingredients.length > 1">✕</button>
      </div>
      <button class="btn-outline btn-sm mb-1" @click="addRow">+ Aggiungi ingrediente</button>
      <p style="font-size:.8rem;color:#888;">Somma: {{ form.ingredients.reduce((s, r) => s + r.proportion, 0).toFixed(2) }}</p>
      <p v-if="error" style="color:#dc2626;font-size:.85rem;margin-top:.5rem;">{{ error }}</p>
      <button class="mt-1 btn-green" @click="submit">Salva blend</button>
    </div>

    <div class="card" v-if="!loading">
      <table v-if="blends.length">
        <tr><th>ID</th><th>Nome</th><th>Ingredienti</th><th>Azioni</th></tr>
        <tr v-for="b in blends" :key="b.id">
          <td>{{ b.id }}</td>
          <td><strong>{{ b.name }}</strong></td>
          <td class="text-xs">{{ b.ingredients?.map(i => `${i.ingredient_name || '?'} ${(i.proportion*100).toFixed(0)}%`).join(', ') || '-' }}</td>
          <td><button class="btn-danger btn-sm" @click="remove(b.id)">🗑</button></td>
        </tr>
      </table>
      <p v-else class="text-sm text-xs">Nessun blend creato.</p>
    </div>
  </div>
</template>
