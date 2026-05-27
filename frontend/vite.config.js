import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/chat': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        // Only proxy POST requests (API calls). GET /chat is the React chat page.
        bypass: (req) => req.method !== 'POST' ? req.url : null,
      },
      '/health': { target: 'http://localhost:8000', changeOrigin: true },
    },
  },
  build: {
    sourcemap: false,
    chunkSizeWarningLimit: 500,
  },
})
