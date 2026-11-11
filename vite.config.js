import { resolve } from 'node:path'
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Project-page deploy: served from https://wongi-jang.github.io/ml-conference-reports/
export default defineConfig({
  base: '/ml-conference-reports/',
  plugins: [react()],
  build: {
    rollupOptions: {
      // one page per venue; src/pages.js holds the nav that links them
      input: {
        main: resolve(__dirname, 'index.html'),
        neurips: resolve(__dirname, 'neurips.html'),
      },
    },
  },
})
