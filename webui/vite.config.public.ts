import { defineConfig, type Plugin } from 'vite';
import react from '@vitejs/plugin-react';
import path from 'path';

// Vite (7.x) keeps the input HTML's filename in the output, so an entry named
// public.html would be served as dist-public/public.html. The public nginx
// image serves index.html, so rename it during bundling.
const renameIndex = (from: string, to: string): Plugin => ({
  name: 'rename-index-html',
  // post: run after vite:build-html emits the HTML asset in generateBundle
  enforce: 'post',
  generateBundle(_options, bundle) {
    for (const [fileName, chunkOrAsset] of Object.entries(bundle)) {
      if (fileName === from && chunkOrAsset.type === 'asset') {
        delete bundle[fileName];
        chunkOrAsset.fileName = to;
        bundle[to] = chunkOrAsset;
      }
    }
  },
});

// Public build: curated analytics-only entry. Serves behind nginx with /api proxied.
export default defineConfig({
  plugins: [react(), renameIndex('public.html', 'index.html')],
  // Flag for src/lib/buildMode.ts: public builds link comments straight to
  // Reddit instead of opening the admin-only comment-detail modal.
  define: { __PUBLIC_BUILD__: 'true' },
  resolve: {
    alias: { '@': path.resolve(__dirname, './src') },
  },
  // Dev server proxy so `vite --config vite.config.public.ts` works with the
  // existing backend on :8000 (same contract as the admin dev config).
  server: {
    port: 3100,
    strictPort: true,
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: 'dist-public',
    sourcemap: false,
    minify: 'esbuild',
    chunkSizeWarningLimit: 1000,
    rollupOptions: {
      input: path.resolve(__dirname, 'public.html'),
      output: {
        manualChunks: { vendor: ['react', 'react-dom', 'react-router-dom'] },
      },
    },
  },
});
