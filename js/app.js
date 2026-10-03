(function () {
  "use strict";
  var C = window.GALI_CONFIG;
  var $ = function (s) { return document.querySelector(s); };
  var state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size };

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
  $("#hero-poster").innerHTML = GaliPoster.svg({
    seed: byId(C.cities, "delhi").seed, theme: byId(C.themes, "blue"), aspect: 4 / 3,
    label: "Sample poster: street network in white lines on blue"
  });

  // ---- selects & theme radios ----
  function fill(sel, items, fmt) {
    sel.innerHTML = items.map(function (i) { return '<option value="' + esc(i.id) + '">' + esc(fmt(i)) + "</option>"; }).join("");
  }
  var pickCity = $("#pick-city"), fCity = $("#f-city"), fSize = $("#f-size"), fTheme = $("#f-theme");
  var cityLabel = function (c) { return c.name + (c.soon ? " (preview only)" : ""); };
  fill(pickCity, C.cities, cityLabel);
  fill(fCity, C.cities, cityLabel);
  fCity.insertAdjacentHTML("beforeend", '<option value="other">Other city (tell us below)</option>');
  fill(fSize, C.sizes, function (s) { return s.label + " — " + money(s.price); });
  fill(fTheme, C.themes, function (t) { return t.name; });

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
    var theme = byId(C.themes, state.theme), size = byId(C.sizes, state.size);
    var city = C.cities.filter(function (c) { return c.id === state.city; })[0];
    var svg = GaliPoster.svg({
      seed: city ? city.seed : 99, theme: theme, aspect: aspect(size),
      label: "Preview: " + (city ? city.name : "custom city") + " in " + theme.name + " (placeholder pattern)"
    });
    $("#picker-preview").innerHTML = svg;
    $("#order-preview").innerHTML = svg;
    picker.querySelectorAll("input").forEach(function (i) { i.checked = i.value === state.theme; });
    fTheme.value = state.theme; fSize.value = state.size; fCity.value = state.city;
    if (city) pickCity.value = state.city;
    $("#price").textContent = money(size.price);
  }
  render();

  // ---- gallery ----
  function galleryItem(p) {
    var theme = byId(C.themes, p.theme);
    var art = p.image
      ? '<img src="' + esc(p.image) + '" alt="' + esc(p.alt || p.title) + '" loading="lazy" width="600" height="800">'
      : GaliPoster.svg({ seed: p.seed, theme: theme, aspect: 4 / 3, label: p.alt || p.title });
    return '<li class="card"><figure><div class="art">' + art + "</div><figcaption>" + esc(p.title) + "</figcaption></figure></li>";
  }
  function showGallery(list, note) {
    $("#gallery-grid").innerHTML = list.map(galleryItem).join("");
    $("#gallery-note").textContent = note || "";
  }
  var PLACEHOLDER_NOTE = "Sample patterns for the staging site, not real maps. Real posters are drawn from OpenStreetMap data.";
  fetch("data/posters.json").then(function (r) { if (!r.ok) throw 0; return r.json(); })
    .then(function (d) { showGallery(d.posters, PLACEHOLDER_NOTE); })
    .catch(function () {
      // e.g. opened via file:// where fetch is blocked: fall back to one sample per theme
      showGallery(C.themes.slice(0, 8).map(function (t, i) {
        return { title: "Delhi — " + t.name, theme: t.id, seed: 11 + i * 0, image: null };
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
      size: size.label, theme: byId(C.themes, fTheme.value).name,
      name: $("#f-name").value.trim(), email: $("#f-email").value.trim(), notes: $("#f-notes").value.trim(),
      price: size.price, currency: C.currency.code, submittedAt: new Date().toISOString()
    };
    var done = function () {
      show("Thank you, " + payload.name.split(" ")[0] + "! Your request is in. We'll email " + payload.email + " shortly.");
      if (C.payment.link) { var a = $("#pay-link"); a.href = C.payment.link; a.textContent = C.payment.label; $("#pay-wrap").classList.remove("hidden"); }
      form.reset(); state = { city: C.defaults.city, theme: C.defaults.theme, size: C.defaults.size }; $("#other-city-wrap").classList.add("hidden"); render();
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
