import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';  // для React

export default defineConfig({
  server: {
    host: '0.0.0.0',
    port: 5173,
    proxy: {
      '/api': {
        target: 'http://backend:8000', // имя сервиса в Docker-сети
        changeOrigin: true,
        rewrite: (path) => path.replace(/^\/api/, '/api') // сохраняем /api в пути
      }
    }
  }
});