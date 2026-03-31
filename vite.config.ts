import { defineConfig } from 'vite';
import { resolve } from 'path';

export default defineConfig({
  root: 'static',
  publicDir: '../static', // 公共文件目录（原样复制）
  build: {
    outDir: '../dist',
    emptyOutDir: true,
    base: '/',
    // 资源内联/复制配置
    assetsDir: 'assets',
    // 不破坏相对路径
    rollupOptions: {
      input: {
        main: resolve(__dirname, 'static/index.html'),
      },
    },
    // 复制 publicDir 到 outDir
    copyPublicDir: true,
  },
  server: {
    port: 5173,
    proxy: {
      '/api': {
        target: 'https://xuanxue-app-production.up.railway.app',
        changeOrigin: true,
        secure: true,
      },
    },
  },
});
