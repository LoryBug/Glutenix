import { defineConfig } from 'vite'
import vue from '@vitejs/plugin-vue'

export default defineConfig({
  plugins: [vue()],
  server: {
    proxy: {
      '/ingredients': 'http://localhost:8000',
      '/applications': 'http://localhost:8000',
      '/blends': 'http://localhost:8000',
      '/simulate': 'http://localhost:8000',
      '/predict': 'http://localhost:8000',
      '/optimize': 'http://localhost:8000',
      '/experiments': 'http://localhost:8000',
      '/health': 'http://localhost:8000',
    }
  }
})
