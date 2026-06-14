<script setup>
import { ref, onMounted } from 'vue'
import { useRouter, useRoute } from 'vue-router'
import { getHealth } from './api/client'

const router = useRouter()
const route = useRoute()
const healthy = ref(false)

onMounted(async () => {
  try { await getHealth(); healthy.value = true } catch { healthy.value = false }
})

const nav = [
  { name: 'Dashboard', path: '/' },
  { name: 'Ingredienti', path: '/ingredients' },
  { name: 'Blend', path: '/blends' },
  { name: 'Simula', path: '/simulate' },
  { name: 'Predici', path: '/predict' },
  { name: 'Ottimizza', path: '/optimize' },
]
</script>

<template>
  <div class="app-layout">
    <header>
      <div class="logo" @click="router.push('/')">
        <span class="logo-icon">&#127837;</span>
        <span class="logo-text">Glutenix</span>
        <span class="logo-badge" :class="{ on: healthy }">{{ healthy ? 'online' : 'offline' }}</span>
      </div>
      <nav>
        <button v-for="item in nav" :key="item.path"
          class="nav-btn" :class="{ active: route.path === item.path }"
          @click="router.push(item.path)">{{ item.name }}</button>
      </nav>
    </header>
    <main>
      <router-view />
    </main>
  </div>
</template>

<style scoped>
.app-layout { min-height: 100vh; display: flex; flex-direction: column; }
header {
  background: #fff; border-bottom: 1px solid #e5e7eb; padding: .6rem 1.5rem;
  display: flex; align-items: center; justify-content: space-between;
  position: sticky; top: 0; z-index: 10;
}
.logo { display: flex; align-items: center; gap: .5rem; cursor: pointer; }
.logo-icon { font-size: 1.4rem; }
.logo-text { font-size: 1.2rem; font-weight: 700; color: #1e3a5f; }
.logo-badge {
  font-size: .65rem; padding: .1rem .45rem; border-radius: 99px; font-weight: 600;
  background: #fef3c7; color: #92400e;
}
.logo-badge.on { background: #dcfce7; color: #166534; }
nav { display: flex; gap: .25rem; }
.nav-btn {
  background: transparent; color: #555; padding: .4rem .8rem; border-radius: 6px; font-size: .85rem;
}
.nav-btn:hover { background: #f3f4f6; color: #111; }
.nav-btn.active { background: #eff6ff; color: #2563eb; font-weight: 600; }
main { flex: 1; padding: 1.5rem; max-width: 1100px; width: 100%; margin: 0 auto; }
</style>
