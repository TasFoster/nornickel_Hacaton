import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// Дев-сервер на :5173; запросы /api проксируются на Django (:8000), чтобы не ловить CORS.
// В проде фронт собирается статикой (dist/) и обращается к бэкенду по VITE_API_BASE.
export default defineConfig(({ command }) => ({
  plugins: [react()],
  build: { outDir: 'dist' },
  server: {
    // Явный IPv4: на Windows 'localhost' часто резолвится в 127.0.0.1, а IPv6-биндинг (::1)
    // делает дев-сервер и прокси недоступными. Держим и сервер, и прокси-таргет на 127.0.0.1.
    host: '127.0.0.1',
    port: 5173,
    // Прокси нужен только дев-серверу; в прод-сборке он не участвует.
    proxy: command === 'serve'
      ? { '/api': { target: 'http://127.0.0.1:8000', changeOrigin: true } }
      : undefined,
  },
}));
