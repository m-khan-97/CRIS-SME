import { defineConfig, loadEnv, type Plugin } from 'vite'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'
import { readFileSync } from 'node:fs'

// https://vite.dev/config/
export default defineConfig(({ command, mode }) => {
  const enterprise = mode === 'enterprise' || loadEnv(mode, process.cwd()).VITE_ENTERPRISE_MODE === 'true';
  const target = enterprise ? 'http://127.0.0.1:8788' : 'http://127.0.0.1:8787';
  return ({
  define: { 'import.meta.env.VITE_ENTERPRISE_MODE': JSON.stringify(String(enterprise)) },
  publicDir: enterprise ? false : 'public',
  // Demo mode and self-host mode both build a bundle served at "/" (demo:
  // static, no backend; selfhost: same origin as the Docker-packaged
  // local_runner, full live functionality). Regular production builds land
  // in dist/site/console/ and resolve under "/console/". Dev server stays at
  // "/" so the proxy rules work.
  base: mode === 'demo' || mode === 'selfhost' || mode === 'enterprise' ? '/' : command === 'build' ? '/console/' : '/',
  plugins: [react(), tailwindcss(), ...(enterprise ? [{ name: 'enterprise-public-assets',
    generateBundle() { this.emitFile({ type: 'asset', fileName: 'favicon.svg', source: readFileSync(new URL('./public/favicon.svg', import.meta.url)) }); },
  } satisfies Plugin] : [])],
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
        target,
        changeOrigin: true,
      },
      '/outputs': {
        target,
        changeOrigin: true,
      },
      '/health': {
        target,
        changeOrigin: true,
      },
    },
  },
})})
