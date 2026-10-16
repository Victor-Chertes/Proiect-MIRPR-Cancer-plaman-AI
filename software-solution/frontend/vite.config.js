import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// Requests to /api are forwarded to the Flask backend during development.
export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': 'http://127.0.0.1:5000',
    },
  },
})
