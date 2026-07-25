import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => ({
  // Demo mode and self-host mode both build a bundle served at "/" (demo:
  // static, no backend; selfhost: same origin as the Docker-packaged
  // local_runner, full live functionality). Regular production builds land
  // in dist/site/console/ and resolve under "/console/". Dev server stays at
  // "/" so the proxy rules work.
  base: mode === 'demo' || mode === 'selfhost' ? '/' : command === 'build' ? '/console/' : '/',
  plugins: [react(), tailwindcss()],
  build: {
    rollupOptions: {
      output: {
        // Route-level code splitting (App.tsx lazy()) handles most of the win;
        // these two libs are only used by 2-3 routes each but are heavy enough
        // (charting, graph layout) to warrant their own vendor chunks so they
        // don't inflate the shared entry bundle every route pays for.
        manualChunks(id: string) {
          if (id.includes('node_modules/recharts')) return 'charts'
          if (id.includes('node_modules/@xyflow')) return 'flow'
        },
      },
    },
  },
  server: {
    proxy: {
      '/api': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/outputs': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
      '/health': {
        target: 'http://127.0.0.1:8787',
        changeOrigin: true,
      },
    },
  },
}))
