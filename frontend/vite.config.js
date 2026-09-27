import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

const backend = 'http://127.0.0.1:8000'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    // Same-origin proxy: session and CSRF cookies work without CORS.
    proxy: {
      '/api': backend,
      '/admin': backend,
      '/static': backend,
    },
  },
})
