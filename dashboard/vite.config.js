import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// base './' so the production build also works when opened from a subpath or file server
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    proxy: {
      // during `npm run dev`, API calls go to the FastAPI backend
      '/api': 'http://127.0.0.1:8000',
    },
  },
})
