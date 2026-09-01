/**
 * Vite 8 在 Windows 上无法加载 .ts/.mjs 配置文件（rolldown bug），
 * 使用 configFile: false + 程序化构建绕过。
 *
 * 用法: node build.js
 */
const { build } = require('vite');
const react = require('@vitejs/plugin-react');
const { VitePWA } = require('vite-plugin-pwa');

build({
  configFile: false,
  plugins: [
    react(),
    VitePWA({
      registerType: 'autoUpdate',
      includeAssets: ['pwa-192x192.png', 'pwa-512x512.png'],
      manifest: {
        name: 'AI经营决策平台',
        short_name: 'AI经营',
        theme_color: '#1677ff',
        background_color: '#ffffff',
        display: 'standalone',
        start_url: '/',
        scope: '/',
        lang: 'zh-CN',
        icons: [
          { src: '/pwa-192x192.png', sizes: '192x192', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png' },
          { src: '/pwa-512x512.png', sizes: '512x512', type: 'image/png', purpose: 'maskable' },
        ],
      },
      workbox: {
        navigateFallback: '/index.html',
        runtimeCaching: [
          { urlPattern: /^https?:\/\/.*\/api\/.*/i, handler: 'NetworkOnly' },
        ],
      },
    }),
  ],
  build: {
    outDir: 'dist',
    emptyOutDir: false,
    sourcemap: false,
    chunkSizeWarningLimit: 1500,
    rollupOptions: {
      output: {
        manualChunks(id) {
          if (id.includes('node_modules/react') || id.includes('node_modules/react-dom') || id.includes('node_modules/react-router-dom')) return 'react-vendor';
          if (id.includes('node_modules/antd') || id.includes('node_modules/@ant-design')) return 'antd-vendor';
          if (id.includes('node_modules/echarts') || id.includes('node_modules/echarts-for-react')) return 'echarts-vendor';
        },
      },
    },
  },
}).then(() => console.log('BUILD OK')).catch(e => { console.error('BUILD FAIL:', e.message); process.exit(1); });
