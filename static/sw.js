// 玄学互动平台 Service Worker
const CACHE_NAME = 'xuanxue-v3';
const STATIC_ASSETS = [
  '/',
  '/static/index.html',
  '/static/style.css',
  '/static/script.js',
  '/static/manifest.json',
  '/static/icon-48.png',
  '/static/icon-72.png',
  '/static/icon-96.png',
  '/static/icon-144.png',
  '/static/icon-192.png',
  '/static/icon-512.png',
];

// 安装：缓存静态资源
self.addEventListener('install', event => {
  event.waitUntil(
    caches.open(CACHE_NAME).then(cache => {
      console.log('[SW] Caching static assets');
      return cache.addAll(STATIC_ASSETS);
    }).then(() => self.skipWaiting())
  );
});

// 激活：清理旧缓存
self.addEventListener('activate', event => {
  event.waitUntil(
    caches.keys().then(keys => {
      return Promise.all(
        keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k))
      );
    }).then(() => self.clients.claim())
  );
});

// 请求拦截
self.addEventListener('fetch', event => {
  const url = new URL(event.request.url);

  // API 请求：网络优先，回退缓存
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then(response => {
          // 缓存成功的 API 响应
          if (response.ok) {
            const clone = response.clone();
            caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
          }
          return response;
        })
        .catch(() => {
          // 网络失败，返回缓存
          return caches.match(event.request);
        })
    );
    return;
  }

  // 静态资源：缓存优先
  event.respondWith(
    caches.match(event.request).then(cached => {
      if (cached) return cached;
      return fetch(event.request).then(response => {
        if (response.ok && event.request.method === 'GET') {
          const clone = response.clone();
          caches.open(CACHE_NAME).then(cache => cache.put(event.request, clone));
        }
        return response;
      });
    })
  );
});

// 推送通知（未来扩展）
self.addEventListener('push', event => {
  const data = event.data ? event.data.json() : {};
  const title = data.title || '玄学互动';
  const body = data.body || '您有新的运势解读';
  event.waitUntil(self.registration.showNotification(title, { body, icon: '/static/icon-192.png' }));
});
