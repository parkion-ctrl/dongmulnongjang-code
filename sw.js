// 배포 스크립트가 __BUILD__ 를 배포 시각으로 바꿔서, 배포할 때마다 새 캐시를 쓴다.
const CACHE = 'dongmulnongjang-__BUILD__';
// 묶음 파일은 배포 스크립트가 ?v=배포시각 을 붙인다(index.html과 같은 주소)
const CORE = ['./', './index.html', './manifest.json', './assets/sprites_bundle.js?v=__BUILD__', './assets/food_data.js?v=__BUILD__'];

self.addEventListener('install', e => {
  // 브라우저 HTTP 캐시에 남은 옛 파일을 받지 않도록 항상 서버에서 새로 받는다
  e.waitUntil(caches.open(CACHE).then(c => c.addAll(CORE.map(u => new Request(u, { cache: 'reload' })))));
  self.skipWaiting();
});

self.addEventListener('activate', e => {
  e.waitUntil(caches.keys().then(keys => Promise.all(keys.filter(k => k !== CACHE).map(k => caches.delete(k)))));
  self.clients.claim();
});

self.addEventListener('fetch', e => {
  const req = e.request;
  if (req.method !== 'GET' || new URL(req.url).origin !== location.origin) return;
  const isPage = req.mode === 'navigate' || req.destination === 'document';
  if (isPage) {
    // 화면은 항상 최신을 먼저 받고, 오프라인일 때만 캐시
    e.respondWith(fetch(req).then(res => {
      const copy = res.clone();
      caches.open(CACHE).then(c => c.put(req, copy));
      return res;
    }).catch(() => caches.match(req).then(hit => hit || caches.match('./index.html'))));
    return;
  }
  // 그림 등은 캐시를 먼저 쓰고, 없으면 받아서 저장
  e.respondWith(caches.match(req).then(hit => hit || fetch(req).then(res => {
    const copy = res.clone();
    caches.open(CACHE).then(c => c.put(req, copy));
    return res;
  })));
});
