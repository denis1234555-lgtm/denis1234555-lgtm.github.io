// 動動腦小學堂 離線快取。遊戲更新時，把版本號加 1。
const CACHE = 'ddn-v89';
const AUDIO = 'ddn-audio'; // AI 語音音檔另外存，換版本也不用重新下載
const CORE = ['./', './index.html', './manifest.webmanifest', './icon-192.png', './icon-512.png', './apple-touch-icon.png'];

self.addEventListener('install', e => {
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE)).then(() => self.skipWaiting()));
});
self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE && k !== AUDIO).map(k => caches.delete(k)))).then(() => self.clients.claim()));
});
self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET') return;
  const url = new URL(req.url);
  // 主頁：先上網拿最新版，沒網路就用快取
  if (req.mode === 'navigate') {
    e.respondWith(fetch(req).then(res => { const copy = res.clone(); caches.open(CACHE).then(c => c.put('./index.html', copy)); return res; })
      .catch(() => caches.match('./index.html')));
    return;
  }
  // AI 語音：音檔做好就不會變，先用快取；清單先上網拿最新的
  if (url.origin === location.origin && url.pathname.includes('/audio/v/')) {
    if (url.pathname.endsWith('.mp3')) {
      e.respondWith(caches.open(AUDIO).then(c => c.match(req).then(hit => hit || fetch(req).then(res => { if (res && res.status === 200) c.put(req, res.clone()); return res; }))));
    } else {
      e.respondWith(fetch(req).then(res => { if (res && res.ok) { const copy = res.clone(); caches.open(AUDIO).then(c => c.put(req, copy)); } return res; }).catch(() => caches.open(AUDIO).then(c => c.match(req))));
    }
    return;
  }
  // 圖示、字型等：先用快取，背景更新
  if (url.origin === location.origin || /fonts\.(googleapis|gstatic)\.com$/.test(url.hostname) || (url.hostname === 'cdn.jsdelivr.net' && url.pathname.includes('fluent-emoji'))) {
    e.respondWith(caches.match(req).then(hit => {
      const net = fetch(req).then(res => { if (res && (res.ok || res.type === 'opaque')) { const copy = res.clone(); caches.open(CACHE).then(c => c.put(req, copy)); } return res; }).catch(() => hit);
      return hit || net;
    }));
  }
});
