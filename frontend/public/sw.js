/**
 * TerraRisk AI - Progressive Web App (PWA) Service Worker (Phase 8)
 * Implements:
 * 1. Cache-First for local static shell assets and icons.
 * 2. Stale-While-Revalidate for live telemetry, relief camp listings, and active alerts.
 * 3. Offline fallback cache with preloaded disaster emergency helplines & shelter directories.
 */

const CACHE_NAME = 'terrarisk-cache-v1';
const STATIC_ASSETS = [
  '/',
  '/index.html',
  '/favicon.svg',
  '/manifest.json',
  'https://unpkg.com/leaflet@1.9.4/dist/leaflet.css'
];

// Offline Emergency Helpline & Relief Fallback Store
const OFFLINE_EMERGENCY_DATA = {
  helplines: [
    { name: "National Emergency Response (ERSS)", number: "112", desc: "All-in-one Emergency (Police, Fire, Medical, Disaster)" },
    { name: "District Disaster Management (DDMA)", number: "1077", desc: "District Collectorate 24/7 Disaster Control Room" },
    { name: "State Emergency Operations (SEOC)", number: "1070", desc: "Kerala State Disaster Management Authority" },
    { name: "Kerala Fire & Rescue Force", number: "101", desc: "Search and rescue, water extraction, debris clearing" },
    { name: "Emergency Medical Ambulance", number: "108", desc: "Kanivu 108 Free Emergency Ambulance Service" },
    { name: "Kerala Police Control", number: "100", desc: "Law enforcement & traffic corridor clearance" },
    { name: "Forest Dept Emergency Unit", number: "1076", desc: "Forest edge & high altitude hill rescue" }
  ],
  shelters: [
    { id: 1, name: "Meppadi GHSS Relief Camp", district: "Wayanad", lat: 11.5542, lng: 76.1308, capacity: 300, occupied: 85, contact_number: "+91 94470 12345" },
    { id: 2, name: "Kalpetta SKMJ School Shelter", district: "Wayanad", lat: 11.6092, lng: 76.0828, capacity: 500, occupied: 120, contact_number: "+91 94470 23456" },
    { id: 3, name: "Vythiri Community Hall", district: "Wayanad", lat: 11.5500, lng: 76.0400, capacity: 200, occupied: 40, contact_number: "+91 94470 34567" },
    { id: 4, name: "Munnar Govt College Camp", district: "Idukki", lat: 10.0889, lng: 77.0595, capacity: 400, occupied: 95, contact_number: "+91 94470 45678" }
  ]
};

// Install Event: Pre-cache core shell
self.addEventListener('install', (event) => {
  event.waitUntil(
    caches.open(CACHE_NAME).then((cache) => {
      console.log('[PWA Service Worker] Pre-caching core shell assets...');
      return cache.addAll(STATIC_ASSETS).catch((err) => {
        console.warn('[PWA Service Worker] Asset pre-cache partial warning:', err);
      });
    })
  );
  self.skipWaiting();
});

// Activate Event: Cleanup outdated caches
self.addEventListener('activate', (event) => {
  event.waitUntil(
    caches.keys().then((cacheNames) => {
      return Promise.all(
        cacheNames.map((cache) => {
          if (cache !== CACHE_NAME) {
            console.log('[PWA Service Worker] Removing outdated cache:', cache);
            return caches.delete(cache);
          }
        })
      );
    })
  );
  self.clients.claim();
});

// Fetch Strategy: Stale-While-Revalidate with Offline Fallback
self.addEventListener('fetch', (event) => {
  const url = new URL(event.request.url);

  // Ignore non-GET requests or browser extension protocols
  if (event.request.method !== 'GET' || !url.protocol.startsWith('http')) {
    return;
  }

  // API Requests: Stale-While-Revalidate with JSON Fallback for shelters/health
  if (url.pathname.startsWith('/api/')) {
    event.respondWith(
      fetch(event.request)
        .then((networkResponse) => {
          // Cache successful API responses for offline resilience
          if (networkResponse && networkResponse.status === 200) {
            const clone = networkResponse.clone();
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
          }
          return networkResponse;
        })
        .catch(async () => {
          // Network failed (device is offline) -> check cache
          const cachedResponse = await caches.match(event.request);
          if (cachedResponse) {
            return cachedResponse;
          }

          // Fallback response for shelters endpoint when offline
          if (url.pathname.includes('/api/shelters')) {
            return new Response(JSON.stringify({
              success: true,
              count: OFFLINE_EMERGENCY_DATA.shelters.length,
              shelters: OFFLINE_EMERGENCY_DATA.shelters,
              offline_cached: true
            }), {
              headers: { 'Content-Type': 'application/json' }
            });
          }

          return new Response(JSON.stringify({
            success: false,
            offline: true,
            error: "Device is currently offline. Operating on cached local disaster matrix."
          }), {
            status: 503,
            headers: { 'Content-Type': 'application/json' }
          });
        })
    );
    return;
  }

  // Static Assets: Cache-First strategy
  event.respondWith(
    caches.match(event.request).then((cachedResponse) => {
      if (cachedResponse) {
        // Fetch in background to revalidate cache
        fetch(event.request).then((networkResponse) => {
          if (networkResponse && networkResponse.status === 200) {
            caches.open(CACHE_NAME).then((cache) => cache.put(event.request, networkResponse));
          }
        }).catch(() => {});
        return cachedResponse;
      }

      return fetch(event.request).then((networkResponse) => {
        if (networkResponse && networkResponse.status === 200) {
          const clone = networkResponse.clone();
          caches.open(CACHE_NAME).then((cache) => cache.put(event.request, clone));
        }
        return networkResponse;
      }).catch(async () => {
        // If navigating to a page offline, serve root index.html
        if (event.request.mode === 'navigate') {
          return caches.match('/index.html');
        }
      });
    })
  );
});
