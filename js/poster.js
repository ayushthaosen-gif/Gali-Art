/*
 * Poster preview renderer (layout 1a: centred map, anchored footer).
 * The street pattern is a deterministic PLACEHOLDER generated from a seed, not a real map;
 * real maps come from /generator. All geometry comes from data/layout.json (fractions of
 * poster width W) so this preview and the print file can't drift apart.
 */
(function () {
  "use strict";

  var W = 600; // viewBox width; everything else is a fraction of this
  var PREVIEW_BOOST = 2.2; // real print hairlines are far too thin to see in a small preview
  var uid = 0;
  var cache = {};

  // Fallback used when data/layout.json can't be fetched (e.g. file://). Keep identical to that file.
  var layout = {
    map: { top: 0.12, width: 0.80, aspect: 0.978 }, footer: { bottom: 0.10 },
    city: { size: 0.072, track: 0.42 }, rule: { w: 0.07, h: 0.001, above: 0.032, below: 0.028 },
    region: { size: 0.0155, track: 0.36 }, coords: { size: 0.014, track: 0.12, above: 0.011 },
    year: { size: 0.014, track: 0.12, above: 0.011 }, date: { size: 0.014, track: 0.12, above: 0.011 },
    detail: { size: 0.0165, track: 0.03, above: 0.026 }, mark: { size: 0.02, halo: 1.7 },
    roads: { t1: 0.0016, t2: 0.0011, t5: 0.00042 }, mix: { minor: 0.30 }
  };

  function rng(seed) {
    var a = seed | 0;
    return function () {
      a = (a + 0x6d2b79f5) | 0;
      var t = Math.imul(a ^ (a >>> 15), 1 | a);
      t = (t + Math.imul(t ^ (t >>> 7), 61 | t)) ^ t;
      return ((t ^ (t >>> 14)) >>> 0) / 4294967296;
    };
  }
  function f(n) { return Math.round(n * 10) / 10; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function rgb(h) { h = h.replace("#", ""); return [0, 2, 4].map(function (i) { return parseInt(h.substr(i, 2), 16); }); }
  function mix(a, b, t) { // t = share of b
    var A = rgb(a), B = rgb(b);
    return "#" + A.map(function (v, i) { return ("0" + Math.round(v * (1 - t) + B[i] * t).toString(16)).slice(-2); }).join("");
  }

  function fmtCoords(lat, lon) {
    return Math.abs(lat).toFixed(4) + "° " + (lat >= 0 ? "N" : "S") + ", " + Math.abs(lon).toFixed(4) + "° " + (lon >= 0 ? "E" : "W");
  }

  // Irregular rotated lattice with dropped edges (minor), continuous avenues (major),
  // a few diagonals and a ring road (arterial), inside a map box of MW x MH.
  function build(seed, density, MW, MH) {
    var key = seed + ":" + density + ":" + MW;
    if (cache[key]) return cache[key];
    var r = rng(seed);
    var pMinor = 0.5 + 0.34 * density;
    var rmax = MW * 0.5 * (0.35 + 0.65 * density) * 1.02; // older eras: smaller city
    var ang = (-14 + r() * 8) * Math.PI / 180;
    var cx = MW / 2, cy = MH / 2, span = Math.max(MW, MH) * 1.5;

    function steps(total, avg) {
      var out = [], p = -total / 2;
      while (p < total / 2) { out.push(p); p += avg * (0.55 + r() * 0.9); }
      return out;
    }
    var xs = steps(span, 26), ys = steps(span, 26);
    var cs = Math.cos(ang), sn = Math.sin(ang);
    var nodes = xs.map(function (x) {
      return ys.map(function (y) {
        var jx = x + (r() - 0.5) * 5, jy = y + (r() - 0.5) * 5;
        return [cx + jx * cs - jy * sn, cy + jx * sn + jy * cs];
      });
    });
    var majX = {}, majY = {};
    for (var m = 2; m < xs.length; m += 3 + Math.floor(r() * 3)) majX[m] = 1;
    for (m = 2; m < ys.length; m += 3 + Math.floor(r() * 3)) majY[m] = 1;

    var minor = "", major = "", art = "", i, j, a, b;
    function inside(a, b) { return Math.hypot((a[0] + b[0]) / 2 - cx, (a[1] + b[1]) / 2 - cy) <= rmax; }
    function seg(a, b) { return "M" + f(a[0]) + " " + f(a[1]) + "L" + f(b[0]) + " " + f(b[1]); }
    for (i = 0; i < xs.length; i++) {
      for (j = 0; j < ys.length; j++) {
        a = nodes[i][j];
        if (i + 1 < xs.length) {
          b = nodes[i + 1][j];
          if (!inside(a, b)) { r(); } else if (majY[j]) major += seg(a, b); else if (r() < pMinor) minor += seg(a, b);
        }
        if (j + 1 < ys.length) {
          b = nodes[i][j + 1];
          if (!inside(a, b)) { r(); } else if (majX[i]) major += seg(a, b); else if (r() < pMinor) minor += seg(a, b);
        }
      }
    }
    for (i = 0; i < 3; i++) { // diagonals
      var d = ang + (0.5 + r() * 0.9) * (r() < 0.5 ? 1 : -1);
      var px = MW * (0.3 + r() * 0.4), py = MH * (0.3 + r() * 0.4), L = Math.min(span / 2, rmax);
      art += seg([px - Math.cos(d) * L, py - Math.sin(d) * L], [px + Math.cos(d) * L, py + Math.sin(d) * L]);
    }
    var rr = Math.min(MW * (0.26 + r() * 0.06), rmax * 0.9), ox = cx + (r() - 0.5) * 30, oy = cy + (r() - 0.5) * 30, ring = "";
    for (i = 0; i <= 48; i++) { // ring road
      var t = (i / 48) * Math.PI * 2, k = rr * (1 + 0.06 * Math.sin(t * 3 + seed));
      ring += (i ? "L" : "M") + f(ox + Math.cos(t) * k) + " " + f(oy + Math.sin(t) * k * 1.1);
    }
    art += ring;
    return (cache[key] = { minor: minor, major: major, art: art });
  }

  // Footer stack laid out bottom-up from the bottom margin, all in viewBox units.
  function footer(H, o) {
    var L = layout, out = { texts: [], rule: null }, cursor = H - L.footer.bottom * W;
    function line(spec, text, lh, mono, upper, gapAbove) {
      var s = spec.size * W, h = lh * s, top = cursor - h;
      out.texts.push({ text: upper ? text.toUpperCase() : text, s: s, track: spec.track * s, mono: mono, y: top + h / 2 + 0.35 * s });
      cursor = top - gapAbove * W;
    }
    var ds = L.date || L.year, dt = L.detail;
    // optional detail line closes the stack in Jost sentence case after a larger gap, so the mono data block above never changes
    if (o.detail) line(dt, o.detail, 1.2, false, false, dt.above);
    if (o.date) line(ds, o.date, 1.2, true, false, ds.above);
    line(L.year, String(o.year), 1.2, true, false, L.year.above);
    if (o.coords) line(L.coords, o.coords, 1.2, true, false, L.coords.above);
    if (o.region) line(L.region, o.region, 1.2, false, true, L.rule.below);
    var rh = L.rule.h * W, rtop = cursor - rh;
    out.rule = { x: (W - L.rule.w * W) / 2, y: rtop, w: L.rule.w * W, h: rh };
    cursor = rtop - L.rule.above * W;
    line(L.city, o.city, 1, false, true, 0);
    return out;
  }

  window.GaliPoster = {
    setLayout: function (l) { layout = l; cache = {}; },
    fmtCoords: fmtCoords,
    /**
     * svg({ seed, theme:{bg,line}, aspect (h/w), density, city, region, lat, lon, year, label })
     * Returns an SVG string. city/year are drawn in the footer.
     */
    svg: function (o) {
      var L = layout, aspect = o.aspect || 4 / 3, H = Math.round(W * aspect);
      var MW = L.map.width * W, MH = MW / L.map.aspect;
      var p = o.mapImage ? null : build(o.seed || 1, o.density || 1, MW, MH);
      var id = "gp" + (uid++), line = o.theme.line, bg = o.theme.bg;
      var minorC = mix(line, bg, L.mix.minor);
      var label = o.label || "Placeholder street-map poster";
      var coords = o.lat != null ? fmtCoords(o.lat, o.lon) : "";
      var ft = footer(H, { city: o.city || "Your city", region: o.region || "", coords: coords, year: o.year || 2025, date: o.date || "", detail: o.detail || "" });
      var sw = function (ratio) { return f(ratio * W * PREVIEW_BOOST * 10) / 10; };

      var markLayer = "";
      if (o.mark) { // illustrative marker in map-box coordinates; the real one is placed exactly from the order
        var d = L.mark.size * W * PREVIEW_BOOST, mx = o.mark.x * MW, my = o.mark.y * MH, r = d / 2;
        markLayer = '<circle cx="' + f(mx) + '" cy="' + f(my) + '" r="' + f(r * L.mark.halo) + '" fill="' + bg + '"/>';
        if (o.mark.style === "ring") {
          markLayer += '<circle cx="' + f(mx) + '" cy="' + f(my) + '" r="' + f(r * 0.8) + '" fill="none" stroke="' + line + '" stroke-width="' + f(d * 0.18) + '"/>';
        } else if (o.mark.style === "heart") {
          var hp = "";
          for (var hi = 0; hi <= 40; hi++) {
            var ht = 2 * Math.PI * hi / 40;
            hp += (hi ? "L" : "M") + f(mx + 16 * Math.pow(Math.sin(ht), 3) / 17 * r) + " " +
              f(my - (13 * Math.cos(ht) - 5 * Math.cos(2 * ht) - 2 * Math.cos(3 * ht) - Math.cos(4 * ht)) / 17 * r);
          }
          markLayer += '<path d="' + hp + 'Z" fill="' + line + '"/>';
        } else {
          markLayer += '<circle cx="' + f(mx) + '" cy="' + f(my) + '" r="' + f(r) + '" fill="' + line + '"/>';
        }
      }
      var mapLayer;
      if (o.mapImage) { // real map: one white-lines-on-transparent image used as an alpha mask over the theme line colour
        mapLayer = '<mask id="m' + id + '" maskUnits="userSpaceOnUse" x="0" y="0" width="' + f(MW) + '" height="' + f(MH) + '" mask-type="alpha" style="mask-type:alpha">' +
          '<image href="' + esc(o.mapImage) + '" width="' + f(MW) + '" height="' + f(MH) + '" preserveAspectRatio="none"/></mask>' +
          '<rect width="' + f(MW) + '" height="' + f(MH) + '" fill="' + line + '" mask="url(#m' + id + ')"/>';
      } else {
        mapLayer = '<g clip-path="url(#' + id + ')" fill="none" stroke-linecap="round" stroke-linejoin="round">' +
          '<path d="' + p.minor + '" stroke="' + minorC + '" stroke-width="' + sw(L.roads.t5) + '"/>' +
          '<path d="' + p.major + '" stroke="' + line + '" stroke-width="' + sw(L.roads.t2) + '"/>' +
          '<path d="' + p.art + '" stroke="' + line + '" stroke-width="' + sw(L.roads.t1) + '"/></g>';
      }
      var s = '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + " " + H +
        '" role="img" aria-label="' + esc(label) + '" preserveAspectRatio="xMidYMid slice">' +
        '<rect width="' + W + '" height="' + H + '" fill="' + bg + '"/>' +
        '<clipPath id="' + id + '"><rect width="' + f(MW) + '" height="' + f(MH) + '"/></clipPath>' +
        '<g transform="translate(' + f((W - MW) / 2) + " " + f(L.map.top * W) + ')">' +
        mapLayer + markLayer +
        '</g>' +
        '<rect x="' + f(ft.rule.x) + '" y="' + f(ft.rule.y) + '" width="' + f(ft.rule.w) + '" height="' + f(Math.max(ft.rule.h, 0.3)) + '" fill="' + line + '"/>';
      ft.texts.forEach(function (t) {
        var fam = t.mono ? "'DM Mono', ui-monospace, Menlo, monospace" : "Jost, Futura, 'Century Gothic', system-ui, sans-serif";
        // letter-spacing adds a trailing gap, so nudge right by half of it to stay optically centred
        s += '<text x="' + f(W / 2 + t.track / 2) + '" y="' + f(t.y) + '" text-anchor="middle" fill="' + line +
          '" font-family="' + fam + '" font-size="' + f(t.s) + '" letter-spacing="' + f(t.track) + '">' + esc(t.text) + "</text>";
      });
      return s + "</svg>";
    }
  };
})();
