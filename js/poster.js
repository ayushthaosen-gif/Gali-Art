/*
 * Placeholder poster renderer.
 * Generates a deterministic, street-like SVG pattern (not a real map) from a seed,
 * so the picker/gallery can recolour instantly. Real maps come from /generator.
 */
(function () {
  "use strict";

  var W = 600;
  var uid = 0;
  var cache = {};

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

  // Irregular lattice, rotated, with dropped edges (minor), continuous avenues (major),
  // a few diagonals and a ring road.
  function build(seed, H, density) {
    var key = seed + ":" + H + ":" + density;
    if (cache[key]) return cache[key];
    var r = rng(seed);
    var pMinor = 0.5 + 0.34 * density;
    var rmax = Math.hypot(W, H) / 2 * (0.38 + 0.62 * density); // older eras: smaller city
    var ang = (-14 + r() * 8) * Math.PI / 180;
    var cx = W / 2, cy = H / 2, span = Math.max(W, H) * 1.5;

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

    var minor = "", major = "", i, j, a, b;
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
    // diagonals
    for (i = 0; i < 3; i++) {
      var d = ang + (0.5 + r() * 0.9) * (r() < 0.5 ? 1 : -1);
      var px = W * (0.15 + r() * 0.7), py = H * (0.15 + r() * 0.7), L = Math.min(span / 2, rmax);
      major += seg([px - Math.cos(d) * L, py - Math.sin(d) * L], [px + Math.cos(d) * L, py + Math.sin(d) * L]);
    }
    // ring road
    var rr = Math.min(W * (0.26 + r() * 0.06), rmax * 0.9), ox = cx + (r() - 0.5) * 40, oy = cy + (r() - 0.5) * 40, ring = "";
    for (i = 0; i <= 48; i++) {
      var t = (i / 48) * Math.PI * 2, k = rr * (1 + 0.06 * Math.sin(t * 3 + seed));
      ring += (i ? "L" : "M") + f(ox + Math.cos(t) * k) + " " + f(oy + Math.sin(t) * k * 1.1);
    }
    major += ring;
    return (cache[key] = { minor: minor, major: major });
  }

  /**
   * poster.svg({ seed, theme:{bg,line}, aspect (h/w), title, label })
   * Returns an SVG string.
   */
  window.GaliPoster = {
    svg: function (o) {
      var aspect = o.aspect || 4 / 3;
      var H = Math.round(W * aspect);
      var p = build(o.seed || 1, H, o.density || 1);
      var id = "gp" + (uid++), m = W * 0.07;
      var label = o.label || "Placeholder street-map poster";
      return '<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 ' + W + " " + H +
        '" role="img" aria-label="' + label.replace(/"/g, "&quot;") + '" preserveAspectRatio="xMidYMid slice">' +
        '<rect width="' + W + '" height="' + H + '" fill="' + o.theme.bg + '"/>' +
        '<clipPath id="' + id + '"><rect x="' + m + '" y="' + m + '" width="' + (W - 2 * m) + '" height="' + (H - 2 * m) + '"/></clipPath>' +
        '<g clip-path="url(#' + id + ')" fill="none" stroke="' + o.theme.line + '" stroke-linecap="round">' +
        '<path d="' + p.minor + '" stroke-width="0.9" opacity="0.85"/>' +
        '<path d="' + p.major + '" stroke-width="2.4"/></g>' +
        '<rect x="' + m + '" y="' + m + '" width="' + (W - 2 * m) + '" height="' + (H - 2 * m) + '" fill="none" stroke="' + o.theme.line + '" stroke-width="0.8" opacity="0.5"/>' +
        "</svg>";
    }
  };
})();
