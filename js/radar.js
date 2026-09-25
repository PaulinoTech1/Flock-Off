/* Radar tab: proximity alerts for known ALPR cameras, no hardware required.
 * Uses the phone's GPS + the same OSM camera data as the map. Everything runs
 * locally; the only network traffic is the camera-data fetch itself.
 * Audio: WebAudio beeps, rate increases as you close in (radar-detector style).
 */
"use strict";

const RadarTab = (() => {
  let watchId = null;
  let audioCtx = null;
  let cameras = [];
  let lastBeep = 0;
  let running = false;

  function el(id) { return document.getElementById(id); }

  function ensureAudio() {
    if (!audioCtx) {
      const AC = window.AudioContext || window.webkitAudioContext;
      if (AC) audioCtx = new AC();
    }
    if (audioCtx && audioCtx.state === "suspended") audioCtx.resume();
  }

  function beep(freq, ms) {
    if (!audioCtx || !el("radar-sound").checked) return;
    const t = audioCtx.currentTime;
    const osc = audioCtx.createOscillator();
    const gain = audioCtx.createGain();
    osc.type = "sine";
    osc.frequency.value = freq;
    gain.gain.setValueAtTime(0.25, t);
    gain.gain.exponentialRampToValueAtTime(0.001, t + ms / 1000);
    osc.connect(gain).connect(audioCtx.destination);
    osc.start(t);
    osc.stop(t + ms / 1000);
  }

  async function toggle() {
    if (running) { stop(); return; }
    if (!navigator.geolocation) {
      setStatus("Geolocation is not available in this browser.");
      return;
    }
    ensureAudio(); // user gesture: safe to create/resume AudioContext
    running = true;
    el("radar-toggle").textContent = "Stop radar";
    el("radar-toggle").setAttribute("aria-pressed", "true");
    setStatus("Acquiring position and loading nearby cameras...");
    try {
      const pos = await getPosition();
      cameras = await CameraData.fetchAround(
        pos.coords.latitude, pos.coords.longitude, FLOCKOFF_CONFIG.radarCacheKm
      );
      el("radar-count").textContent =
        `${cameras.length} known cameras within ${FLOCKOFF_CONFIG.radarCacheKm} km loaded.`;
    } catch (err) {
      setStatus(`Radar needs position + camera data: ${err.message}`);
      stop();
      return;
    }
    watchId = navigator.geolocation.watchPosition(onPosition, onGeoError, {
      enableHighAccuracy: true, maximumAge: 5000, timeout: 15000,
    });
  }

  function getPosition() {
    return new Promise((resolve, reject) =>
      navigator.geolocation.getCurrentPosition(resolve, reject, {
        enableHighAccuracy: true, timeout: 15000,
      })
    );
  }

  function onPosition(pos) {
    const { latitude, longitude, accuracy } = pos.coords;
    let nearest = null;
    let best = Infinity;
    for (const cam of cameras) {
      const d = CameraData.distM(latitude, longitude, cam.lat, cam.lon);
      if (d < best) { best = d; nearest = cam; }
    }
    const cfg = FLOCKOFF_CONFIG;
    const banner = el("radar-banner");
    if (nearest && best <= cfg.radarWarnM) {
      const urgent = best <= cfg.radarAlertM;
      banner.hidden = false;
      banner.className = "banner " + (urgent ? "banner-alert" : "banner-warn");
      banner.textContent =
        `${urgent ? "ALPR within " : "ALPR ahead: "}${Math.round(best)} m ` +
        `(${nearest.isFlock ? "Flock Safety" : nearest.brand}, ${nearest.operator}). ` +
        `GPS accuracy +/-${Math.round(accuracy || 0)} m.`;
      const now = Date.now();
      const interval = urgent ? 900 : 2200; // beep faster when closer
      if (now - lastBeep > interval) {
        lastBeep = now;
        beep(urgent ? 1320 : 880, 120);
      }
    } else {
      banner.hidden = true;
      banner.className = "banner";
      banner.textContent = "";
      const label = nearest
        ? `Nearest known camera: ${Math.round(best / 100) / 10} km away.`
        : "No known cameras in the loaded set.";
      setStatus(`${label} GPS accuracy +/-${Math.round(accuracy || 0)} m.`);
    }
  }

  function onGeoError() {
    setStatus("GPS signal lost. Radar paused; move to open sky or stop and restart.");
  }

  function stop() {
    running = false;
    if (watchId !== null) navigator.geolocation.clearWatch(watchId);
    watchId = null;
    const btn = el("radar-toggle");
    btn.textContent = "Start radar";
    btn.setAttribute("aria-pressed", "false");
    el("radar-banner").hidden = true;
    setStatus("Radar off.");
  }

  function setStatus(msg) { el("radar-status").textContent = msg; }

  function init() {
    el("radar-toggle").addEventListener("click", toggle);
    window.addEventListener("beforeunload", stop);
  }

  return { init };
})();
