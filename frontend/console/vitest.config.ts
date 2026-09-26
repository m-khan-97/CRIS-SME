import { defineConfig } from 'vitest/config'
import react from '@vitejs/plugin-react'
import tailwindcss from '@tailwindcss/vite'

export default defineConfig({
  plugins: [react(), tailwindcss()],
  test: {
    environment: 'jsdom',
    include: ['src/**/*.test.{ts,tsx}'],
    coverage: {
      provider: 'v8',
      include: ['src/**/*.{ts,tsx}'],
      exclude: ['src/test/**', 'src/vite-env.d.ts', 'src/api/types.ts', 'src/api/reportSections.ts'],
      reporter: ['text', 'json-summary', 'lcov'],
      thresholds: { statements: 58, branches: 44, functions: 42, lines: 60 },
    },
    setupFiles: ['./src/test/setup.ts'],
    css: false,
  },
})
