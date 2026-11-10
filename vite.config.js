import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

// Project-page deploy: served from https://wongi-jang.github.io/iclr2027-report/
export default defineConfig({
  base: '/iclr2027-report/',
  plugins: [react()],
})
