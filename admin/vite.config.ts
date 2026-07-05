import react from '@vitejs/plugin-react';
import { defineConfig } from 'vite';

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      // Lokalni razvoj bez Dockera: proxy API poziva na Traefik/backend
      '/api': 'http://localhost',
    },
  },
});
