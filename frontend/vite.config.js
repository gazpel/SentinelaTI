import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// En desarrollo, /api se redirige a la API FastAPI (uvicorn en el puerto 8000).
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      '/api': { target: process.env.SENTINELA_API ?? 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
})
