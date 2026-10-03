(function () {
  "use strict";
  var C = window.GALI_CONFIG;
  var $ = function (s) { return document.querySelector(s); };
  var state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size, era: C.defaults.era, frame: C.defaults.frame || "none", mat: false, detail: "none" };

  function byId(list, id) { return list.filter(function (x) { return x.id === id; })[0] || list[0]; }
  function esc(s) { return String(s).replace(/[&<>"]/g, function (c) { return { "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]; }); }
  function money(n) { return new Intl.NumberFormat(C.currency.locale, { style: "currency", currency: C.currency.code, maximumFractionDigits: 0 }).format(n); }
  function aspect(size) { return size.h / size.w; }
  // Only offer map years that exist as a real map for at least one city; the rest would be invented patterns.
  var ERAS = C.eras.filter(function (e) { return C.cities.some(function (c) { return c.maps && c.maps[e.id]; }); });
  // Optional detail line under the year. Facts come from config (computed from the map data); they describe the current map only.
  var nf = new Intl.NumberFormat(C.currency.locale);
  function detailOptions(city, eraId) {
    var o = [{ id: "none", label: "None" }], f = city && eraId === C.defaults.era && city.facts;
    if (f && f.streetsKm) o.push({ id: "streets", label: "Street length", text: nf.format(f.streetsKm) + " km of streets mapped" });
    if (f && f.areaKm2) o.push({ id: "area", label: "City area", text: nf.format(f.areaKm2) + " km² area" });
    if (f && f.streetsKm && f.areaKm2) o.push({ id: "both", label: "Area and street length", text: nf.format(f.areaKm2) + " km² · " + nf.format(f.streetsKm) + " km of streets mapped" });
    o.push({ id: "custom", label: "Your own words" });
    return o;
  }
  function detailText(city, eraId) {
    var opt = detailOptions(city, eraId).filter(function (x) { return x.id === state.detail; })[0];
    if (!opt || opt.id === "none") return "";
    return opt.id === "custom" ? cleanDetail($("#f-detail-text").value) : opt.text;
  }
  // tidy what the customer typed (design 5d): one line, " - " becomes " · ", curly quotes and apostrophes, max 40 characters, case as typed
  function cleanDetail(text) {
    var t = String(text || "").replace(/\s+/g, " ").trim().replace(/ [-–—] /g, " · ");
    t = t.replace(/(^|[\s(\[])"/g, "$1“").replace(/"/g, "”").replace(/(^|[\s(\[])'/g, "$1‘").replace(/'/g, "’");
    return t.slice(0, 40).replace(/\s+$/, "");
  }
  function framePrice(frame, size) { return (frame.price && frame.price[size.id]) || 0; }
  function matPrice(size) { return (C.mat && C.mat.price && C.mat.price[size.id]) || 0; }
  // The framed preview (frame-preview/frame.js) draws the frame and mat to scale in millimetres around our live poster SVG.
  // It only knows sizes by its own keys; prices, finishes and the mat toggle all stay in our config and form.
  var FRAME_SIZE = { a4: "A4", a3: "A3", "18x24": "18x24" };
  function mountFrame(id) { try { return window.FramePreview ? FramePreview.mount($(id)) : null; } catch (e) { return null; } }
  var orderFrame = mountFrame("#order-framed"), miniFrame = mountFrame("#mini-framed");
  function cityOf(id) { return C.cities.filter(function (c) { return c.id === id; })[0]; }
  // a city we have no map for ("Other") can only show the current year
  function hasMap(city, eraId) { return city ? !!(city.maps && city.maps[eraId]) : eraId === C.defaults.era; }
  var VQ = "?v=" + encodeURIComponent(C.version || "dev");

  // ---- brand ----
  document.title = C.brand.name + " | Custom city street-map posters";
  document.querySelectorAll("[data-brand]").forEach(function (e) { e.textContent = C.brand.name; });
  document.querySelectorAll("[data-brand-native]").forEach(function (e) { e.textContent = C.brand.nameNative || ""; e.hidden = !C.brand.nameNative; });
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
    if (city && city.maps && city.maps[String(year)]) o.mapImage = city.maps[String(year)] + VQ; // real map for this city + year
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
  var fDetail = $("#f-detail"), fDetailText = $("#f-detail-text");
  var pickCity = $("#pick-city"), fCity = $("#f-city"), fSize = $("#f-size"), fTheme = $("#f-theme"), fEra = $("#f-era"), fFrame = $("#f-frame"), fMat = $("#f-mat");
  var cityLabel = function (c) { return c.name + (c.soon ? " (preview only)" : ""); };
  fill(pickCity, C.cities, cityLabel);
  fill(fCity, C.cities, cityLabel);
  fCity.insertAdjacentHTML("beforeend", '<option value="other">Other city (tell us below)</option>');
  fill(fSize, C.sizes, function (s) { return s.label + ", " + money(s.price); });
  fill(fTheme, C.themes, function (t) { return t.name; });
  fFrame.addEventListener("change", function () { set({ frame: fFrame.value, mat: !!byId(C.frames, fFrame.value).matDefault }); });
  fMat.addEventListener("change", function () { set({ mat: fMat.checked }); });
  fDetail.addEventListener("change", function () { set({ detail: fDetail.value }); });
  fDetailText.addEventListener("input", function () { render(); });
  fill(fEra, ERAS, function (e) { return e.year + (e.year === 2025 ? " (current)" : ""); });
  var eraPicker = $("#era-picker");
  eraPicker.insertAdjacentHTML("beforeend", ERAS.map(function (e) {
    return '<label class="era"><input type="radio" name="era" value="' + esc(e.id) + '"><span>' + e.year + "</span></label>";
  }).join(""));
  eraPicker.addEventListener("change", function (e) { if (e.target.name === "era") set({ era: e.target.value }); });
  fEra.addEventListener("change", function () { set({ era: fEra.value }); });
  $("#f-date").addEventListener("input", function () { render(); });
  fill($("#f-area"), C.areas, function (x) { return x.label; });
  fill($("#f-mark"), C.marks, function (x) { return x.label; });
  ["#f-area", "#f-mark", "#f-set"].forEach(function (id) { $(id).addEventListener("change", function () { render(); }); });

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

  // ---- gallery: the framed cards and the room scene follow the city, colour and map-year pickers ----
  // Their sizes are fixed by the markup (data-size), so the main size selector never changes the scale comparison.
  var FRAME_TO_SIZE = { A4: "a4", A3: "a3", "18x24": "18x24" };
  var galleryPosters = [].map.call(document.querySelectorAll("#gallery .framed .poster"), function (poster) {
    var framed = poster.closest(".framed");
    return { poster: poster, city: framed.dataset.city || "", size: byId(C.sizes, FRAME_TO_SIZE[framed.dataset.size]) };
  });
  function renderGallery(city, theme, era) {
    var current = byId(C.eras, C.defaults.era);
    galleryPosters.forEach(function (g) {
      // slides that name a city always show it (current map); the others follow the city and map-year pickers
      var c = g.city ? cityOf(g.city) : city, e = g.city ? current : era;
      var o = posterOpts(c, e.year);
      o.theme = theme; o.aspect = aspect(g.size); o.density = e.density;
      o.label = (c ? c.name : "Sample") + " " + e.year + " poster in " + theme.name + ", " + g.size.label.split(" (")[0];
      g.poster.innerHTML = GaliPoster.svg(o);
    });
    var white = byId(C.frames, "white"), avoid = !!(white.avoid && white.avoid.indexOf(theme.id) >= 0);
    $("#white-note").textContent = avoid ? "White wood can look washed out around " + theme.name + "." : "";
    $("#white-note").classList.toggle("hidden", !avoid);
  }

  function render() {
    var theme = byId(C.themes, state.theme), size = byId(C.sizes, state.size), frame = byId(C.frames, state.frame);
    if (!frame.matAllowed) state.mat = false; // no mat with this finish
    var mat = !!state.mat;
    var city = cityOf(state.city);
    // a year with no real map for this city falls back to the current map
    if (city && !hasMap(city, state.era)) state.era = C.defaults.era;
    var era = byId(C.eras, state.era);
    var dopts = detailOptions(city, state.era);
    if (!dopts.some(function (x) { return x.id === state.detail; })) state.detail = "none"; // that fact doesn't apply to this city or year
    var o = posterOpts(city, era.year);
    o.theme = theme; o.aspect = aspect(size); o.density = era.density; o.date = fmtDate($("#f-date").value); o.detail = detailText(city, state.era);
    o.label = "Preview: " + (city ? city.name : "custom city") + " " + era.year + " in " + theme.name + (city ? "" : " (sample pattern; your city is drawn from real map data)");
    var markId = $("#f-mark").value;
    if (markId !== "none") o.mark = { style: markId, x: city && city.markDemo ? city.markDemo.x : 0.5, y: city && city.markDemo ? city.markDemo.y : 0.5 };
    $("#centre-wrap").classList.toggle("hidden", $("#f-area").value === "city");
    $("#markat-wrap").classList.toggle("hidden", markId === "none");
    // then & now pair: an older year plus the matching 2025 poster; only where both maps are real
    var canPair = state.era !== C.defaults.era && hasMap(city, C.defaults.era) && hasMap(city, state.era);
    $("#set-wrap").classList.toggle("hidden", !canPair);
    if (!canPair) $("#f-set").checked = false;
    var pair = $("#f-set").checked;
    $("#f-set-label").textContent = "Make it a then & now pair: add the matching " + C.defaults.era + " poster (save " + Math.round(C.pairDiscount * 100) + "%)";
    var svg = GaliPoster.svg(o);
    $("#picker-preview").innerHTML = svg;
    renderGallery(city, theme, era);
    // the order preview hangs the same poster on the wall, in the chosen frame; the colour picker above shows it bare.
    // The small copy beside the frame field matters on phones, where the main preview has scrolled out of view.
    var hasFrame = frame.id !== "none", look = { frame: frame.id, mat: mat, size: FRAME_SIZE[size.id] || "A3" };
    $("#order-poster").innerHTML = svg; $("#mini-poster").innerHTML = svg;
    if (orderFrame) orderFrame.set(look);
    if (miniFrame) miniFrame.set(look);
    var cap = (city ? city.name : "Your city") + " · " + era.year;
    $("#picker-caption").textContent = cap;
    $("#order-caption").textContent = cap + (hasFrame ? " · " + frame.name + (mat ? " with mat" : "") : "");
    eraPicker.querySelectorAll("input").forEach(function (i) { i.checked = i.value === state.era; i.disabled = !hasMap(city, i.value); });
    [].forEach.call(fEra.options, function (opt) { opt.disabled = !hasMap(city, opt.value); });
    fEra.value = state.era;
    $("#era-note").textContent = !city ? "" : ERAS.some(function (e) { return e.id !== C.defaults.era && hasMap(city, e.id); })
      ? (C.eraNote || "") : city.name + " only has a 2025 map for now.";
    picker.querySelectorAll("input").forEach(function (i) { i.checked = i.value === state.theme; });
    fTheme.value = state.theme; fSize.value = state.size; fCity.value = state.city;
    fill(fFrame, C.frames, function (f) { var p = framePrice(f, size); return f.name + (p ? " (+" + money(p) + ")" : ""); });
    fFrame.value = state.frame;
    $("#f-mat-wrap").classList.toggle("hidden", !frame.matAllowed);
    fMat.checked = mat;
    $("#f-mat-label").textContent = C.mat.name + " (+" + money(matPrice(size)) + ")";
    $("#frame-spec").textContent = hasFrame ? frame.spec + (mat ? " " + C.mat.spec : "") + " " + (frame.note || "") : "";
    var warn = !!(frame.avoid && frame.avoid.indexOf(state.theme) >= 0);
    $("#frame-hint").textContent = warn ? frame.name + " can look washed out around the " + theme.name + " poster. Black wood or natural oak suit it better." : "";
    $("#frame-hint").classList.toggle("hidden", !warn);
    fill(fDetail, dopts, function (x) { return x.label; });
    fDetail.value = state.detail;
    fDetailText.classList.toggle("hidden", state.detail !== "custom");
    if (city) pickCity.value = state.city;
    var fp = framePrice(frame, size) + (mat ? matPrice(size) : 0);
    var one = size.price + fp, total = pair ? Math.round(one * 2 * (1 - C.pairDiscount)) : one;
    $("#price").textContent = money(total);
    var detailTxt = fp ? size.label.split(" (")[0] + " " + money(size.price) + " + " + frame.name.toLowerCase() + (mat ? " with mat " : " ") + money(fp) : "";
    $("#price-detail").textContent = pair ? "2 posters (" + era.year + " and " + C.defaults.era + "), " + Math.round(C.pairDiscount * 100) + "% off. " + detailTxt : detailTxt;
  }
  render();

  // ---- shared layout (data/layout.json); falls back to built-in defaults if it can't be fetched ----
  var layoutReady = fetch("data/layout.json" + VQ).then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (l) { GaliPoster.setLayout(l); renderHero(); render(); })
    .catch(function () {});

  // ---- swipeable carousel: section buttons, dots and arrows follow the swipe and jump to a slide ----
  [].forEach.call(document.querySelectorAll(".swipe"), function (row) {
    var items = [].slice.call(row.children), nav = document.createElement("div"), dots = document.createElement("div"), current = 0;
    var seg = row.previousElementSibling && row.previousElementSibling.classList.contains("seg") ? row.previousElementSibling : null;
    nav.className = "swipe-nav"; dots.className = "swipe-dots";
    function go(i) { i = Math.max(0, Math.min(items.length - 1, i)); items[i].scrollIntoView({ behavior: "smooth", inline: "start", block: "nearest" }); }
    function arrow(label, glyph, dir) {
      var b = document.createElement("button");
      b.type = "button"; b.className = "swipe-arrow"; b.setAttribute("aria-label", label); b.textContent = glyph;
      b.addEventListener("click", function () { go(current + dir); });
      return b;
    }
    var prev = arrow("Previous slide", "\u2039", -1), next = arrow("Next slide", "\u203a", 1);
    items.forEach(function (item, i) {
      var b = document.createElement("button");
      b.type = "button"; b.setAttribute("aria-label", "Show slide " + (i + 1) + " of " + items.length);
      b.addEventListener("click", function () { go(i); });
      dots.appendChild(b);
    });
    nav.appendChild(prev); nav.appendChild(dots); nav.appendChild(next);
    row.insertAdjacentElement("afterend", nav);
    if (seg) [].forEach.call(seg.children, function (b) { b.addEventListener("click", function () { go(Number(b.dataset.slide)); }); });
    function mark(i) {
      current = i;
      [].forEach.call(dots.children, function (d, k) { if (k === i) d.setAttribute("aria-current", "true"); else d.removeAttribute("aria-current"); });
      prev.disabled = i === 0; next.disabled = i === items.length - 1;
      if (seg) {
        var active = null;
        [].forEach.call(seg.children, function (b) { if (Number(b.dataset.slide) <= i) active = b; });
        [].forEach.call(seg.children, function (b) { b.setAttribute("aria-pressed", String(b === active)); });
      }
    }
    mark(0);
    // the active slide is the one nearest the row's left edge (more than one slide can be mostly visible on wide screens)
    var queued = false;
    function sync() {
      queued = false;
      var left = row.getBoundingClientRect().left, best = 0, gap = Infinity;
      items.forEach(function (item, i) { var d = Math.abs(item.getBoundingClientRect().left - left); if (d < gap) { gap = d; best = i; } });
      if (row.scrollLeft <= 2) best = 0;
      else if (row.scrollLeft >= row.scrollWidth - row.clientWidth - 2) best = items.length - 1;
      if (best !== current) mark(best);
    }
    row.addEventListener("scroll", function () { if (!queued) { queued = true; requestAnimationFrame(sync); } }, { passive: true });
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
      detail: detailText(cityOf(state.city), state.era), size: size.label, frame: byId(C.frames, fFrame.value).name + (state.mat && byId(C.frames, fFrame.value).matAllowed ? " with " + C.mat.name.toLowerCase() : ""), framePrice: framePrice(byId(C.frames, fFrame.value), size) + (state.mat && byId(C.frames, fFrame.value).matAllowed ? matPrice(size) : 0), theme: byId(C.themes, fTheme.value).name, mapYear: byId(C.eras, fEra.value).year, printDate: fmtDate($("#f-date").value),
      name: $("#f-name").value.trim(), email: $("#f-email").value.trim(), notes: $("#f-notes").value.trim(),
      price: 0, currency: C.currency.code, submittedAt: new Date().toISOString(),
      pair: $("#f-set").checked, area: byId(C.areas, $("#f-area").value).label, centreOn: $("#f-area").value === "city" ? "" : $("#f-centre").value.trim(),
      mark: $("#f-mark").value, markAt: $("#f-mark").value === "none" ? "" : $("#f-markat").value.trim()
    };
    payload.price = size.price + payload.framePrice;
    if (payload.pair) payload.price = Math.round(payload.price * 2 * (1 - C.pairDiscount));
    var done = function () {
      show("Thanks, " + payload.name.split(" ")[0] + ". We've got your request and will email you at " + payload.email + " soon.");
      if (C.payment.link) { var a = $("#pay-link"); a.href = C.payment.link; a.textContent = C.payment.label; $("#pay-wrap").classList.remove("hidden"); }
      form.reset(); state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size, era: C.defaults.era, frame: C.defaults.frame || "none", mat: false, detail: "none" }; $("#other-city-wrap").classList.add("hidden"); render();
    };
    if (!C.form.endpoint) { // no order inbox configured: hand the request to the customer's email app instead of dropping it
      var lines = ["Order request (" + payload.brand + ")", "",
        "City: " + payload.city, "Map year: " + payload.mapYear, "Size: " + payload.size, "Frame: " + payload.frame,
        payload.detail ? "Detail line: " + payload.detail : "", "Colour theme: " + payload.theme, payload.printDate ? "Print date: " + payload.printDate : "",
        payload.pair ? "Then & now pair: yes (2 posters: " + payload.mapYear + " and " + C.defaults.era + ")" : "",
        payload.area !== byId(C.areas, "city").label ? "Area: " + payload.area + ", centred on " + payload.centreOn : "",
        payload.mark !== "none" ? "Marker: " + payload.mark + " at " + payload.markAt : "",
        "Total: " + money(payload.price), "", "Name: " + payload.name, "Email: " + payload.email,
        payload.notes ? "Notes: " + payload.notes : ""].filter(function (l, i, a) { return l !== "" || a[i - 1] !== ""; });
      window.location.href = "mailto:" + C.brand.email + "?subject=" + encodeURIComponent("Poster order: " + payload.city + ", " + payload.mapYear) +
        "&body=" + encodeURIComponent(lines.join("\n"));
      show("Your email app should open with the order filled in. Press send and we'll get it. If nothing opens, email us at " + C.brand.email + ".");
      return;
    }
    btn.disabled = true; btn.textContent = "Sending…";
    var opts = C.form.mode === "no-cors"
      ? { method: "POST", mode: "no-cors", headers: { "Content-Type": "text/plain" }, body: JSON.stringify(payload) }
      : { method: "POST", headers: { "Content-Type": "application/json", Accept: "application/json" }, body: JSON.stringify(payload) };
    fetch(C.form.endpoint, opts).then(function (r) {
      if (opts.mode !== "no-cors" && !r.ok) throw new Error("HTTP " + r.status);
      done();
    }).catch(function () {
      show("That didn't send. Try again, or email us at " + C.brand.email + ".", true);
    }).then(function () { btn.disabled = false; btn.textContent = "Send order request"; });
  });
})();
