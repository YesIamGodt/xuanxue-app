import type { CapacitorConfig } from '@capacitor/cli';

const config: CapacitorConfig = {
  appId: 'com.xuanxue.app',
  appName: '玄学互动',
  webDir: 'dist',
  android: {
    backgroundColor: '#0F0A1E',
    allowMixedContent: true,
  },
  server: {
    // 连接到 Railway 上的后端 API
    url: 'https://xuanxue-app-production.up.railway.app',
    androidScheme: 'https',
  },
  plugins: {
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#6B21A8',
    },
  },
};

export default config;
