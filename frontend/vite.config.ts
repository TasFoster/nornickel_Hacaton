import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Dev-сервер на :5173; запросы /api проксируются на Django (:8000), чтобы не ловить CORS.
export default defineConfig({
  plugins: [react()],
  server: {
    // Явный IPv4: на Windows 'localhost' часто резолвится в 127.0.0.1, а IPv6-биндинг (::1)
    // делает dev-сервер и прокси недоступными. Держим и сервер, и прокси-таргет на 127.0.0.1.
    host: '127.0.0.1',
    port: 5173,
    proxy: {
      '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true },
    },
  },
});
