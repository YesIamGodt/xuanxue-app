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
    // Android 使用本地打包资源，不从远程加载
  },
  plugins: {
    StatusBar: {
      style: 'DARK',
      backgroundColor: '#6B21A8',
    },
  },
};

export default config;
