import { defineConfig } from 'vite';
import react from '@vitejs/plugin-react';

// base: './' permite servir os assets de qualquer caminho (o FastAPI serve o dist).
// Em dev, o proxy encaminha /api para o servidor FastAPI local.
export default defineConfig({
  plugins: [react()],
  base: './',
  server: {
    port: 5173,
    proxy: { '/api': 'http://localhost:8000' },
  },
});