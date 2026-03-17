import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'
import path from 'path'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  base: '/TokenMachine/', // GitHub Pages base path
  resolve: {
    alias: {
      '@': path.resolve(__dirname, './src'),
    },
  },
  server: {
    port: 1580,
    host: true,
    allowedHosts: ['zhangqijun.cn', '.zhangqijun.cn'],
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/workers': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
      '/gpus': {
        target: 'http://localhost:8000',
        changeOrigin: true,
        secure: false,
      },
    },
  },
})
