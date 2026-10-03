(function () {
  "use strict";
  var C = window.GALI_CONFIG;
  var $ = function (s) { return document.querySelector(s); };
  var state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size, era: C.defaults.era };

  function byId(list, id) { return list.filter(function (x) { return x.id === id; })[0] || list[0]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function money(n) { return new Intl.NumberFormat(C.currency.locale, { style: "currency", currency: C.currency.code, maximumFractionDigits: 0 }).format(n); }
  function aspect(size) { return size.h / size.w; }

  // ---- brand ----
  document.title = C.brand.name + " — custom city street-map posters";
  document.querySelectorAll("[data-brand]").forEach(function (e) { e.textContent = C.brand.name; });
  document.querySelectorAll("[data-tagline]").forEach(function (e) { e.textContent = C.brand.tagline; });
  document.querySelectorAll("[data-email-link]").forEach(function (e) { e.href = "mailto:" + C.brand.email; });

  // ---- mobile menu ----
  var mb = $("#menu-btn"), nav = $("#nav");
  mb.addEventListener("click", function () {
    var open = nav.classList.toggle("open");
    mb.setAttribute("aria-expanded", open);
  });
  nav.addEventListener("click", function (e) { if (e.target.tagName === "A") { nav.classList.remove("open"); mb.setAttribute("aria-expanded", "false"); } });

  // ---- hero ----
  function posterOpts(city, year) {
    var o = city ? { seed: city.seed, city: city.name, region: city.region, lat: city.lat, lon: city.lon, year: year }
                 : { seed: 99, city: "Your city", year: year };
    if (city && city.maps && city.maps[String(year)]) o.mapImage = city.maps[String(year)]; // real map for this city + year
    return o;
  }
  // "2026-02-14" -> "14 FEB 2026" (month abbreviation avoids 14/02 vs 02/14 confusion)
  function fmtDate(iso) {
    var m = /^(\d{4})-(\d{2})-(\d{2})$/.exec(iso || "");
    if (!m) return "";
    return parseInt(m[3], 10) + " " + ["JAN","FEB","MAR","APR","MAY","JUN","JUL","AUG","SEP","OCT","NOV","DEC"][parseInt(m[2], 10) - 1] + " " + m[1];
  }
  function renderHero() {
    var d = byId(C.cities, "delhi"), o = posterOpts(d, 2025);
    o.theme = byId(C.themes, "blue"); o.aspect = 4 / 3;
    o.label = "Sample poster: street network in white lines on blue, captioned Delhi";
    $("#hero-poster").innerHTML = GaliPoster.svg(o);
  }
  renderHero();

  // ---- selects & theme radios ----
  function fill(sel, items, fmt) {
    sel.innerHTML = items.map(function (i) { return '<option value="' + esc(i.id) + '">' + esc(fmt(i)) + "</option>"; }).join("");
  }
  var pickCity = $("#pick-city"), fCity = $("#f-city"), fSize = $("#f-size"), fTheme = $("#f-theme"), fEra = $("#f-era");
  var cityLabel = function (c) { return c.name + (c.soon ? " (preview only)" : ""); };
  fill(pickCity, C.cities, cityLabel);
  fill(fCity, C.cities, cityLabel);
  fCity.insertAdjacentHTML("beforeend", '<option value="other">Other city (tell us below)</option>');
  fill(fSize, C.sizes, function (s) { return s.label + " — " + money(s.price); });
  fill(fTheme, C.themes, function (t) { return t.name; });
  fill($("#f-area"), C.areas, function (x) { return x.label; });
  fill($("#f-mark"), C.marks, function (x) { return x.label; });
  $("#f-dedication").maxLength = C.dedicationMax;
  fill(fEra, C.eras, function (e) { return e.year + (e.year === 2025 ? " (current)" : ""); });
  $("#era-note").textContent = C.eraNote || "";
  var eraPicker = $("#era-picker");
  eraPicker.insertAdjacentHTML("beforeend", C.eras.map(function (e) {
    return '<label class="era"><input type="radio" name="era" value="' + esc(e.id) + '"><span>' + e.year + "</span></label>";
  }).join(""));
  eraPicker.addEventListener("change", function (e) { if (e.target.name === "era") set({ era: e.target.value }); });
  fEra.addEventListener("change", function () { set({ era: fEra.value }); });
  $("#f-date").addEventListener("input", function () { render(); });
  $("#f-dedication").addEventListener("input", function () { render(); });
  $("#f-mark").addEventListener("change", function () { render(); });
  $("#f-set").addEventListener("change", function () { render(); });
  $("#f-area").addEventListener("change", function () { render(); });

  var picker = $("#theme-picker");
  picker.insertAdjacentHTML("beforeend", C.themes.map(function (t) {
    return '<label class="theme"><input type="radio" name="theme" value="' + esc(t.id) + '"><span><i style="background:' + t.bg + ';--l:' + t.line + '"></i>' + esc(t.name) + "</span></label>";
  }).join(""));
  picker.addEventListener("change", function (e) { if (e.target.name === "theme") set({ theme: e.target.value }); });
  pickCity.addEventListener("change", function () { set({ city: pickCity.value }); });
  fCity.addEventListener("change", function () {
    $("#other-city-wrap").classList.toggle("hidden", fCity.value !== "other");
    set({ city: fCity.value });
  });
  fSize.addEventListener("change", function () { set({ size: fSize.value }); });
  fTheme.addEventListener("change", function () { set({ theme: fTheme.value }); });

  function set(patch) { for (var k in patch) state[k] = patch[k]; render(); }

  function render() {
    var theme = byId(C.themes, state.theme), size = byId(C.sizes, state.size), era = byId(C.eras, state.era);
    var city = C.cities.filter(function (c) { return c.id === state.city; })[0];
    var o = posterOpts(city, era.year);
    o.theme = theme; o.aspect = aspect(size); o.density = era.density; o.date = fmtDate($("#f-date").value);
    o.tagline = $("#f-dedication").value.trim();
    var markId = $("#f-mark").value;
    if (markId !== "none") o.mark = { style: markId, x: city && city.markDemo ? city.markDemo.x : 0.5, y: city && city.markDemo ? city.markDemo.y : 0.5 };
    $("#centre-wrap").classList.toggle("hidden", $("#f-area").value === "city");
    $("#markat-wrap").classList.toggle("hidden", markId === "none");
    var canPair = era.id !== "2025";
    $("#set-wrap").classList.toggle("hidden", !canPair);
    if (!canPair) $("#f-set").checked = false;
    var pair = $("#f-set").checked;
    o.label = "Preview: " + (city ? city.name : "custom city") + " " + era.year + " in " + theme.name + " (placeholder pattern)";
    var svg = GaliPoster.svg(o);
    $("#picker-preview").innerHTML = svg;
    var orderEl = $("#order-preview");
    if (pair) {
      var nowOpts = posterOpts(city, 2025);
      nowOpts.theme = theme; nowOpts.aspect = aspect(size); nowOpts.tagline = o.tagline; nowOpts.date = o.date;
      nowOpts.label = "Preview: " + (city ? city.name : "custom city") + " 2025 in " + theme.name + " (matching pair)";
      orderEl.innerHTML = "<div>" + svg + "</div><div>" + GaliPoster.svg(nowOpts) + "</div>";
    } else {
      orderEl.innerHTML = svg;
    }
    orderEl.classList.toggle("pair", pair);
    var cap = (city ? city.name : "Your city") + " · " + era.year;
    $("#picker-caption").textContent = cap;
    $("#order-caption").textContent = cap;
    eraPicker.querySelectorAll("input").forEach(function (i) { i.checked = i.value === state.era; });
    fEra.value = state.era;
    picker.querySelectorAll("input").forEach(function (i) { i.checked = i.value === state.theme; });
    fTheme.value = state.theme; fSize.value = state.size; fCity.value = state.city;
    if (city) pickCity.value = state.city;
    var total = pair ? Math.round(size.price * 2 * (1 - C.pairDiscount)) : size.price;
    $("#price").textContent = money(total);
    $("#price-note").textContent = pair ? "2 posters, " + Math.round(C.pairDiscount * 100) + "% off" : "";
  }
  render();

  // ---- shared layout (data/layout.json); falls back to built-in defaults if it can't be fetched ----
  var layoutReady = fetch("data/layout.json").then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (l) { GaliPoster.setLayout(l); renderHero(); render(); })
    .catch(function () {});

  // ---- gallery ----
  function galleryItem(p) {
    var theme = byId(C.themes, p.theme);
    var o = posterOpts(C.cities.filter(function (c) { return c.id === p.city; })[0], p.year || 2025);
    o.seed = p.seed; o.theme = theme; o.aspect = 4 / 3; o.label = p.alt || p.title;
    var art = p.image
      ? '<img src="' + esc(p.image) + '" alt="' + esc(p.alt || p.title) + '" loading="lazy" width="600" height="800">'
      : GaliPoster.svg(o);
    return '<li class="card"><figure><div class="art">' + art + "</div><figcaption>" + esc(p.title) + "</figcaption></figure></li>";
  }
  function showGallery(list, note) {
    $("#gallery-grid").innerHTML = list.map(galleryItem).join("");
    $("#gallery-note").textContent = note || "";
  }
  var PLACEHOLDER_NOTE = "Delhi (2025) shows the real map. Other cities and earlier years are placeholder patterns on this staging site.";
  fetch("data/posters.json").then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (d) { showGallery(d.posters, PLACEHOLDER_NOTE); })
    .catch(function () {
      // e.g. opened via file:// where fetch is blocked: fall back to one sample per theme
      showGallery(C.themes.slice(0, 8).map(function (t, i) {
        return { title: "Delhi — " + t.name, city: "delhi", theme: t.id, seed: 11, image: null };
      }), PLACEHOLDER_NOTE + " (Serve over http to load data/posters.json.)");
    });

  // ---- order form ----
  var form = $("#order-form"), statusEl = $("#status");
  function setErr(id, msg, input) {
    $(id).textContent = msg;
    if (input) { if (msg) input.setAttribute("aria-invalid", "true"); else input.removeAttribute("aria-invalid"); }
  }
  function validate() {
    var ok = true, name = $("#f-name"), email = $("#f-email"), other = $("#f-other");
    var needOther = fCity.value === "other";
    setErr("#e-other", needOther && !other.value.trim() ? "Please tell us which city." : "", other);
    setErr("#e-name", name.value.trim().length < 2 ? "Please enter your name." : "", name);
    setErr("#e-email", !/^[^\s@]+@[^\s@]+\.[^\s@]{2,}$/.test(email.value.trim()) ? "Please enter a valid email address." : "", email);
    var centre = $("#f-centre"), markAt = $("#f-markat");
    setErr("#e-centre", $("#f-area").value !== "city" && !centre.value.trim() ? "Tell us which place to centre on." : "", centre);
    setErr("#e-markat", $("#f-mark").value !== "none" && !markAt.value.trim() ? "Tell us where to place it." : "", markAt);
    form.querySelectorAll("[aria-invalid=true]").forEach(function () { ok = false; });
    if (!ok) form.querySelector("[aria-invalid=true]").focus();
    return ok;
  }
  function show(msg, bad) {
    statusEl.textContent = msg;
    statusEl.classList.remove("hidden");
    statusEl.classList.toggle("bad", !!bad);
    statusEl.focus();
  }
  form.addEventListener("submit", function (e) {
    e.preventDefault();
    if (form.company.value) return; // honeypot
    if (!validate()) return;
    var size = byId(C.sizes, fSize.value), btn = $("#submit-btn");
    var payload = {
      brand: C.brand.name, city: fCity.value === "other" ? $("#f-other").value.trim() : byId(C.cities, fCity.value).name,
      size: size.label, theme: byId(C.themes, fTheme.value).name, mapYear: byId(C.eras, fEra.value).year, printDate: fmtDate($("#f-date").value),
      name: $("#f-name").value.trim(), email: $("#f-email").value.trim(), notes: $("#f-notes").value.trim(),
      price: $("#f-set").checked ? Math.round(size.price * 2 * (1 - C.pairDiscount)) : size.price, currency: C.currency.code,
      pair: $("#f-set").checked, area: byId(C.areas, $("#f-area").value).label, centreOn: $("#f-area").value === "city" ? "" : $("#f-centre").value.trim(),
      mark: $("#f-mark").value, markAt: $("#f-mark").value === "none" ? "" : $("#f-markat").value.trim(), dedication: $("#f-dedication").value.trim(), submittedAt: new Date().toISOString()
    };
    var done = function () {
      show("Thank you, " + payload.name.split(" ")[0] + "! Your request is in. We'll email " + payload.email + " shortly.");
      if (C.payment.link) { var a = $("#pay-link"); a.href = C.payment.link; a.textContent = C.payment.label; $("#pay-wrap").classList.remove("hidden"); }
      form.reset(); state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size, era: C.defaults.era }; $("#other-city-wrap").classList.add("hidden"); render();
    };
    if (!C.form.endpoint) { // demo mode
      console.info("Demo mode (no form endpoint set in config.js). Payload:", payload);
      done(); show("Demo mode: no form endpoint is configured yet, so nothing was sent. Set form.endpoint in config.js."); return;
    }
    btn.disabled = true; btn.textContent = "Sending…";
    var opts = C.form.mode === "no-cors"
      ? { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain" }, body: JSON.stringify(payload) }
      : { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) };
    fetch(C.form.endpoint, opts).then(function (r) {
      if (opts.mode !== "no-cors" && !r.ok) throw new Error("HTTP " + r.status);
      done();
    }).catch(function () {
      show("Sorry, something went wrong sending your request. Please try again or email " + C.brand.email + ".", true);
    }).then(function () { btn.disabled = false; btn.textContent = "Send order request"; });
  });
})();
