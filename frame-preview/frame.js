/* Keep the original poster node live; all dimensions below are millimetres. */
const FRAMES = {
  black: { face: 20, color: "#1B1B1B", photo: "frame-black.webp", photoSlice: "168", mat: false, matAllowed: false, themes: "all" },
  oak: { face: 20, color: "#C9A77C", texture: "oak.jpg", photo: "frame-oak.webp", photoSlice: "150", mat: true, matAllowed: true,
    themes: ["blue", "forest", "terracotta", "cream"] },
  white: { face: 20, color: "#F3F1EC", photo: "frame-white.webp", photoSlice: "150", mat: false, matAllowed: true,
    themes: ["forest", "midnight", "dark-gold", "blue"], avoid: ["cream", "blush", "mono-grey"] }
};
const MAT = { color: "#FBFAF6", overlap: 5,
  frames: { A4: [300, 400], A3: [400, 500], "18x24": [610, 762] } };
const PRINTS = { A4: [210, 297], A3: [297, 420], "18x24": [457, 610] };
// Illustrative INR prices; replace with actual retail prices before publishing.
const PRICES = {
  currency: "INR", locale: "en-IN", print: { A4: 1499, A3: 2299, "18x24": 2999 },
  frame: { black: { A4: 599, A3: 899, "18x24": 1299 },
    oak: { A4: 699, A3: 999, "18x24": 1399 }, white: { A4: 599, A3: 899, "18x24": 1299 } },
  mat: { A4: 299, A3: 399, "18x24": 599 }
};

(function () {
  "use strict";
  const scriptBase = new URL(".", document.currentScript.src);
  const mounted = new WeakMap();
  const photographs = new Map();
  const reducedMotion = matchMedia("(prefers-reduced-motion: reduce)");
  function photograph(path) {
    if (!photographs.has(path)) {
      const image = new Image();
      const state = { ready: false, failed: false, listeners: new Set() };
      image.onload = () => { state.ready = true; state.listeners.forEach(listener => listener()); state.listeners.clear(); };
      image.onerror = () => { state.failed = true; state.listeners.forEach(listener => listener()); state.listeners.clear(); };
      photographs.set(path, state);
      image.src = new URL(path, scriptBase).href;
    }
    return photographs.get(path);
  }
  function geometry(size, frame, mat) {
    const print = PRINTS[size], inner = mat ? MAT.frames[size] : print, face = FRAMES[frame].face;
    const windowSize = print.map(mm => mm - (mat ? MAT.overlap * 2 : 0));
    return { print, inner, face, outer: inner.map(mm => mm + 2 * face), window: windowSize,
      offset: inner.map((mm, i) => (mm - windowSize[i]) / 2), overlap: mat ? MAT.overlap : 0 };
  }
  function mount(element) {
    if (mounted.has(element)) return mounted.get(element);
    const poster = element.querySelector(":scope > .poster");
    if (!poster) throw new Error("A .framed element needs a direct .poster child");
    const opening = document.createElement("div");
    opening.className = "frame-opening";
    opening.innerHTML = '<div class="frame-paper" aria-hidden="true"></div><div class="frame-bevel" aria-hidden="true"></div><div class="frame-window"><div class="frame-sheet"></div></div><div class="frame-glare" aria-hidden="true"></div>';
    opening.querySelector(".frame-sheet").append(poster);
    element.append(opening);
    ["top", "left", "right", "bottom"].forEach(side => {
      const edge = document.createElement("div");
      edge.className = `frame-edge frame-edge--${side}`;
      edge.setAttribute("aria-hidden", "true"); edge.innerHTML = '<span class="frame-grain"></span>';
      element.append(edge);
    });
    const arris = document.createElement("div"); arris.className = "frame-arris";
    arris.setAttribute("aria-hidden", "true"); element.append(arris);
    const photo = document.createElement("div"); photo.className = "frame-photograph";
    photo.setAttribute("aria-hidden", "true"); element.append(photo);
    const ns = "http://www.w3.org/2000/svg", seams = document.createElementNS(ns, "svg");
    seams.classList.add("frame-seams"); seams.setAttribute("preserveAspectRatio", "none"); seams.setAttribute("aria-hidden", "true");
    for (let i = 0; i < 4; i++) seams.append(document.createElementNS(ns, "line"));
    element.append(seams);
    const scope = element.closest("[data-frame-card]");
    function update() {
      const frame = Object.hasOwn(FRAMES, element.dataset.frame) ? element.dataset.frame : "black";
      const size = Object.hasOwn(PRINTS, element.dataset.size) ? element.dataset.size : "A4";
      const config = FRAMES[frame];
      const mat = config.matAllowed && (element.hasAttribute("data-mat") ? element.dataset.mat === "true" : config.mat);
      element.dataset.frame = frame; element.dataset.size = size; element.dataset.mat = String(mat);
      const g = geometry(size, frame, mat);
      // Use untransformed width: hover tilt changes the bounding rectangle.
      const scale = parseFloat(getComputedStyle(element).width) / g.outer[0];
      const vars = { "face-px": g.face, "outer-height-px": g.outer[1], "window-left": g.offset[0],
        "window-top": g.offset[1], "window-width": g.window[0], "window-height": g.window[1],
        "print-left": -g.overlap, "print-top": -g.overlap, "print-width": g.print[0],
        "print-height": g.print[1], "bevel-px": 2.5, "grain-tile-px": 160 };
      Object.entries(vars).forEach(([key, mm]) => element.style.setProperty(`--${key}`, `${mm * scale}px`));
      element.style.aspectRatio = `${g.outer[0]} / ${g.outer[1]}`;
      element.style.setProperty("--frame-color", config.color); element.style.setProperty("--mat-color", MAT.color);
      const texture = config.texture || (frame === "white" ? FRAMES.oak.texture : null);
      element.style.setProperty("--frame-texture", texture ? `url("${new URL(texture, scriptBase).href}")` : "none");
      if (config.photo) {
        const state = photograph(config.photo);
        element.dataset.photoReady = String(state.ready);
        element.style.setProperty("--frame-photo", `url("${new URL(config.photo, scriptBase).href}")`);
        element.style.setProperty("--frame-photo-slice", config.photoSlice || "12%");
        if (!state.ready && !state.failed) state.listeners.add(update);
      } else element.dataset.photoReady = "false";
      seams.setAttribute("viewBox", `0 0 ${g.outer[0]} ${g.outer[1]}`);
      [[0, 0, g.face, g.face], [g.outer[0], 0, g.outer[0] - g.face, g.face],
        [0, g.outer[1], g.face, g.outer[1] - g.face],
        [g.outer[0], g.outer[1], g.outer[0] - g.face, g.outer[1] - g.face]].forEach((points, i) => {
        ["x1", "y1", "x2", "y2"].forEach((attr, j) => seams.children[i].setAttribute(attr, points[j]));
      });
      if (scope) {
        scope.querySelectorAll("[data-select-frame]").forEach(button => button.setAttribute("aria-pressed", String(button.dataset.selectFrame === frame)));
        const toggle = scope.querySelector("[data-mat-toggle]");
        if (toggle) { toggle.checked = mat; toggle.closest("label").hidden = !config.matAllowed; }
        const price = scope.querySelector("[data-frame-price]");
        if (price) price.textContent = new Intl.NumberFormat(PRICES.locale, { style: "currency", currency: PRICES.currency, maximumFractionDigits: 0 })
          .format(PRICES.print[size] + PRICES.frame[frame][size] + (mat ? PRICES.mat[size] : 0));
        const note = scope.querySelector("[data-frame-note]"), theme = poster.dataset.theme || element.dataset.theme || "blue";
        if (note) { note.hidden = !config.avoid?.includes(theme); note.textContent = "White frames look best with darker themes."; }
        const dimensions = scope.querySelector("[data-frame-dimensions]");
        if (dimensions) dimensions.textContent = `${g.outer[0]} × ${g.outer[1]} mm · 25 mm deep`;
        const title = scope.querySelector("[data-frame-title]");
        if (title) title.textContent = config.label || ({ black: "Matte black", oak: "Natural oak", white: "White stain" }[frame] || frame);
      }
    }
    function set(options) {
      if (options.frame && Object.hasOwn(FRAMES, options.frame)) {
        if (element.dataset.frame !== options.frame) element.dataset.mat = String(FRAMES[options.frame].mat);
        element.dataset.frame = options.frame;
      }
      if (options.mat !== undefined) element.dataset.mat = String(options.mat);
      if (options.size) element.dataset.size = options.size;
      if (options.glazing) element.dataset.glazing = options.glazing;
      update();
      element.dispatchEvent(new CustomEvent("framechange", { bubbles: true, detail: { ...element.dataset } }));
    }
    if (scope) {
      scope.querySelectorAll("[data-select-frame]").forEach(button => button.addEventListener("click", () => set({ frame: button.dataset.selectFrame })));
      scope.querySelector("[data-mat-toggle]")?.addEventListener("change", event => set({ mat: event.target.checked }));
    }
    const observer = new MutationObserver(records => {
      if (records.some(record => record.oldValue !== record.target.getAttribute(record.attributeName))) update();
    });
    observer.observe(element, { attributes: true, attributeOldValue: true, subtree: true,
      attributeFilter: ["data-frame", "data-mat", "data-size", "data-glazing", "data-theme"] });
    const resize = new ResizeObserver(update); resize.observe(element);
    const resetTilt = () => ["tilt-x", "tilt-y", "glare-x", "glare-y"].forEach(key => element.style.removeProperty(`--${key}`));
    element.addEventListener("pointermove", event => {
      if (reducedMotion.matches || element.dataset.tilt !== "true" || event.pointerType !== "mouse") return;
      const box = element.getBoundingClientRect();
      const x = Math.max(-1, Math.min(1, (event.clientX - box.left) / box.width * 2 - 1));
      const y = Math.max(-1, Math.min(1, (event.clientY - box.top) / box.height * 2 - 1));
      element.style.setProperty("--tilt-x", `${-y * 3}deg`); element.style.setProperty("--tilt-y", `${x * 3}deg`);
      element.style.setProperty("--glare-x", `${50 - x * 15}%`); element.style.setProperty("--glare-y", `${50 - y * 15}%`);
    });
    element.addEventListener("pointerleave", resetTilt); reducedMotion.addEventListener("change", resetTilt);
    const api = { element, poster, update, set }; mounted.set(element, api); update(); return api;
  }
  window.FramePreview = { mount, geometry, FRAMES, MAT, PRINTS, PRICES };
  function start() { document.querySelectorAll(".framed").forEach(mount); }
  if (document.readyState === "loading") document.addEventListener("DOMContentLoaded", start, { once: true }); else start();
})();
