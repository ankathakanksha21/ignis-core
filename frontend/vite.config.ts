import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // The FastAPI backend runs on :8000; the app calls it as /api/...
    proxy: { '/api': 'http://localhost:8000' },
  },
})
