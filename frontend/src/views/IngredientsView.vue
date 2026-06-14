<script setup>
import { ref, onMounted } from 'vue'
import { listIngredients, createIngredient, updateIngredient, deleteIngredient } from '../api/client'
import HelpBox from '../components/HelpBox.vue'

const ingredients = ref([])
const loading = ref(true)
const showForm = ref(false)
const editingId = ref(null)

const emptyForm = () => ({ name: '', category: 'flour', protein_pct: null, starch_pct: null, fat_pct: null, fiber_pct: null, kcal_per_100g: null, sugars_pct: null, saturated_fat_pct: null, sodium_mg_per_100g: null })
const form = ref(emptyForm())
const error = ref('')

async function load() {
  loading.value = true
  ingredients.value = await listIngredients().catch(() => [])
  loading.value = false
}

onMounted(load)

async function submit() {
  error.value = ''
  try {
    const payload = { ...form.value }
    for (const k of Object.keys(payload)) {
      if (payload[k] === null || payload[k] === '') payload[k] = null
    }
    await createIngredient(payload)
    form.value = emptyForm()
    showForm.value = false
    await load()
  } catch (e) { error.value = e.response?.data?.detail || e.message }
}

async function remove(id) {
  if (!confirm('Eliminare questo ingrediente?')) return
  try {
    await deleteIngredient(id)
    await load()
  } catch (e) { alert(e.response?.data?.detail || e.message) }
}

function startEdit(ing) {
  editingId.value = ing.id
  form.value = { ...ing }
}

async function saveEdit() {
  error.value = ''
  try {
    const payload = { ...form.value }
    for (const k of Object.keys(payload)) {
      if (payload[k] === null || payload[k] === '') payload[k] = null
    }
    await updateIngredient(editingId.value, payload)
    editingId.value = null
    form.value = emptyForm()
    await load()
  } catch (e) { error.value = e.response?.data?.detail || e.message }
}

function cancelEdit() {
  editingId.value = null
  form.value = emptyForm()
}

function isEditing(ing) {
  return editingId.value === ing.id
}
</script>

<template>
  <div>
    <div class="flex" style="justify-content:space-between;margin-bottom:1rem;">
      <h1>Ingredienti</h1>
      <button @click="showForm = !showForm; editingId = null">{{ showForm ? 'Annulla' : '+ Nuovo ingrediente' }}</button>
    </div>

    <HelpBox title="Aiuto: ingredienti e feature del modello">
      <p>Qui gestisci le materie prime: farine, amidi e idrocolloidi. I valori composizionali e nutrizionali sono salvati per 100g e vengono usati per calcolare le proprieta dei blend.</p>
      <p>Il modello predittivo usa feature derivate dagli ingredienti, come proteine, amido, grassi, fibre, assorbimento acqua, gelatinizzazione, amilosio, viscosita e quota idrocolloidi. Dati ingredienti piu accurati producono blend simulati e predizioni piu affidabili.</p>
    </HelpBox>

    <div v-if="showForm && !editingId" class="card mb-2">
      <h2 style="font-size:.95rem;margin-bottom:.5rem;">Nuovo ingrediente</h2>
      <div class="grid-3">
        <div><label class="text-xs">Nome</label><input v-model="form.name" placeholder="es. Farina di castagne"></div>
        <div><label class="text-xs">Categoria</label>
          <select v-model="form.category"><option>flour</option><option>starch</option><option>hydrocolloid</option></select>
        </div>
        <div><label class="text-xs">Proteine %</label><input v-model.number="form.protein_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Amido %</label><input v-model.number="form.starch_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Grassi %</label><input v-model.number="form.fat_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Fibre %</label><input v-model.number="form.fiber_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Kcal / 100g</label><input v-model.number="form.kcal_per_100g" type="number" step="1"></div>
        <div><label class="text-xs">Zuccheri %</label><input v-model.number="form.sugars_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Gr. saturi %</label><input v-model.number="form.saturated_fat_pct" type="number" step="0.1"></div>
        <div><label class="text-xs">Sodio mg/100g</label><input v-model.number="form.sodium_mg_per_100g" type="number" step="1"></div>
      </div>
      <p v-if="error" style="color:#dc2626;font-size:.85rem;margin-top:.5rem;">{{ error }}</p>
      <button class="mt-1 btn-green" @click="submit">Salva</button>
    </div>

    <div class="card" v-if="!loading">
      <div v-if="ingredients.length" style="overflow-x:auto;">
        <table>
          <tr>
            <th>ID</th><th>Nome</th><th>Categoria</th><th>Proteine</th><th>Amido</th>
            <th>Kcal</th><th>Zuccheri</th><th>Gr.saturi</th><th>Sodio</th><th>Azioni</th>
          </tr>
          <tr v-for="ing in ingredients" :key="ing.id">
            <template v-if="isEditing(ing)">
              <td>{{ ing.id }}</td>
              <td><input v-model="form.name" class="edit-input"></td>
              <td>
                <select v-model="form.category" class="edit-input">
                  <option>flour</option><option>starch</option><option>hydrocolloid</option>
                </select>
              </td>
              <td><input v-model.number="form.protein_pct" type="number" step="0.1" class="edit-input" style="width:5rem;"></td>
              <td><input v-model.number="form.starch_pct" type="number" step="0.1" class="edit-input" style="width:5rem;"></td>
              <td><input v-model.number="form.kcal_per_100g" type="number" step="1" class="edit-input" style="width:5rem;"></td>
              <td><input v-model.number="form.sugars_pct" type="number" step="0.1" class="edit-input" style="width:5rem;"></td>
              <td><input v-model.number="form.saturated_fat_pct" type="number" step="0.1" class="edit-input" style="width:5rem;"></td>
              <td><input v-model.number="form.sodium_mg_per_100g" type="number" step="1" class="edit-input" style="width:5rem;"></td>
              <td>
                <button class="btn-green btn-sm" @click="saveEdit">💾</button>
                <button class="btn-sm" @click="cancelEdit" style="margin-left:.25rem;">✕</button>
              </td>
            </template>
            <template v-else>
              <td>{{ ing.id }}</td>
              <td><strong>{{ ing.name }}</strong></td>
              <td><span class="badge" :class="ing.category">{{ ing.category }}</span></td>
              <td>{{ ing.protein_pct ?? '-' }}%</td>
              <td>{{ ing.starch_pct ?? '-' }}%</td>
              <td>{{ ing.kcal_per_100g ?? '-' }}</td>
              <td>{{ ing.sugars_pct ?? '-' }}%</td>
              <td>{{ ing.saturated_fat_pct ?? '-' }}%</td>
              <td>{{ ing.sodium_mg_per_100g ?? '-' }}</td>
              <td>
                <button class="btn-sm" @click="startEdit(ing)">✏️</button>
                <button class="btn-danger btn-sm" @click="remove(ing.id)">🗑</button>
              </td>
            </template>
          </tr>
        </table>
      </div>
      <p v-else class="text-sm text-xs">Nessun ingrediente trovato.</p>
    </div>
  </div>
</template>

<style scoped>
.edit-input {
  padding: .2rem .35rem; font-size: .8rem; border: 1px solid #d1d5db; border-radius: 4px; width: 100%;
}
</style>
