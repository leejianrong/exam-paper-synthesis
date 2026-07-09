import { defineConfig } from 'vite'
import { svelte } from '@sveltejs/vite-plugin-svelte'

// VITE_API overrides the API origin; defaults to the local FastAPI dev server.
export default defineConfig({
  plugins: [svelte()],
  server: { port: 5173 },
})
