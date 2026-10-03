/*
 * Gali — single configuration file.
 * Rename the brand, change prices, set the form endpoint or payment link here.
 * Nothing in this file is secret: it is shipped to every visitor's browser.
 * Never put API keys or private tokens here.
 */
window.GALI_CONFIG = {
  version: "dev", // stamped with the commit id on deploy (cache busting); leave as is
  brand: {
    name: "Gali", // placeholder brand name — change here only
    nameNative: "गली", // Devanagari line of the logo (shown under the name in the footer); leave "" to hide
    tagline: "Your city, drawn in streets.",
    email: "hello@example.com" // replace with your real contact address
  },

  // Order form submission. Leave endpoint empty to run in demo mode (nothing is sent).
  form: {
    endpoint: "", // e.g. "https://formspree.io/f/xxxxxxx" or a Google Apps Script web-app URL
    mode: "json"  // "json" for Formspree-style endpoints; "no-cors" for Google Apps Script
  },

  // PAYMENT: paste a Razorpay / Stripe payment link here. It is shown after a successful order request.
  // Leave empty to hide the pay button. (No payment code is implemented in this site.)
  payment: {
    link: "",
    label: "Pay securely"
  },

  currency: { code: "INR", locale: "en-IN" },

  // Poster sizes. w/h are only used for the preview's aspect ratio; price is in the currency above.
  sizes: [
    { id: "a4",    label: "A4 (21 × 29.7 cm)",   w: 210, h: 297, price: 1499 },
    { id: "a3",    label: "A3 (29.7 × 42 cm)",   w: 297, h: 420, price: 2299 },
    { id: "18x24", label: "18 × 24 in (46 × 61 cm)", w: 18, h: 24, price: 2999 }
  ],

  // facts: optional detail lines the customer can print under the year. Numbers are computed from the same OpenStreetMap
  // data the poster is drawn from (generator/city_facts.py), rounded; they describe the 2025 map only. areaKm2 is set only
  // where the poster shows the city boundary (not for a square map around the centre). Nothing hand-typed from memory.
  // seed makes each city's placeholder pattern different. Only Delhi is a real product for now.
  cities: [
    // maps: { "<era id>": "<path to white-lines-on-transparent PNG/WebP>" }. A city/year without an entry
    // shows the generated placeholder pattern. Make masks with: generator/batch_masks.py (or make_poster.py --formats mask)
    { id: "delhi", name: "Delhi", seed: 11, region: "India", lat: 28.6139, lon: 77.209,
      facts: { streetsKm: 18400, areaKm2: 1480 },
      maps: { "1995": "assets/delhi-1995-lines.webp", "2025": "assets/delhi-lines.webp" },
      markDemo: { x: 0.715, y: 0.578 } }, // where the preview draws a SAMPLE marker (about India Gate); the real one is placed exactly from the order
    { id: "mumbai", name: "Mumbai", seed: 20, region: "India", lat: 19.076, lon: 72.8777,
      facts: { streetsKm: 4000 },
      maps: { "2025": "assets/mumbai-lines.webp" } },
    { id: "kolkata", name: "Kolkata", seed: 21, region: "India", lat: 22.5726, lon: 88.3639,
      facts: { streetsKm: 3500, areaKm2: 200 },
      maps: { "2025": "assets/kolkata-lines.webp" } },
    { id: "panaji", name: "Panaji", seed: 60, region: "India", lat: 15.4909, lon: 73.8278,
      facts: { streetsKm: 520 },
      maps: { "2025": "assets/panaji-lines.webp" } },
    { id: "dubai", name: "Dubai", seed: 73, region: "United Arab Emirates", lat: 25.2048, lon: 55.2708,
      facts: { streetsKm: 6700 },
      maps: { "2025": "assets/dubai-lines.webp" } },
    { id: "washington-dc", name: "Washington DC", seed: 78, region: "USA", lat: 38.9072, lon: -77.0369,
      facts: { streetsKm: 2000, areaKm2: 180 },
      maps: { "2025": "assets/washington-dc-lines.webp" } },
    // Guwahati: preview only until its real map exists. Generate it (see generator/README.md), then add
    // maps: { "2025": "assets/guwahati-lines.webp" } and remove `soon`.
    { id: "guwahati", name: "Guwahati", seed: 41, region: "Assam, India", lat: 26.1445, lon: 91.7362, soon: true }
  ],

  // Optional frame (design "Frames", launch range 6a-6c): one 20 mm flat-face profile in three finishes; oak and white can add
  // an off-white mat. price is per size id and is ADDED to the poster price. These prices are placeholders: set your real ones.
  // matDefault = choosing this finish switches the mat on (design 6b, oak with mat). avoid = theme ids the finish looks poor with (shown as a gentle hint, not blocked).
  frames: [
    { id: "none",  name: "No frame", price: { a4: 0, a3: 0, "18x24": 0 } },
    { id: "black", name: "Black wood", price: { a4: 599, a3: 899, "18x24": 1299 }, matAllowed: false,
      spec: "20 mm flat face, 25 mm deep, matte black. Acrylic glazing. The print fills the frame edge to edge.",
      note: "Our default. A black edge makes any colour look sharper." },
    { id: "oak",   name: "Natural oak", price: { a4: 699, a3: 999, "18x24": 1399 }, matAllowed: true, matDefault: true,
      spec: "20 mm flat face, 25 mm deep, oak veneer or solid oak. Acrylic glazing.",
      note: "The nicer-looking option. It goes best with Gali Blue, Forest, Terracotta and Cream." },
    { id: "white", name: "White wood", price: { a4: 599, a3: 899, "18x24": 1299 }, matAllowed: true,
      avoid: ["cream", "blush", "mono"],
      spec: "20 mm flat face, 25 mm deep, white stain. Acrylic glazing.",
      note: "Suits light rooms. Looks best around a dark poster: Forest, Midnight, Dark & Gold or Gali Blue." }
  ],
  // Off-white mat (45 degree bevel). The preview draws it to scale from frame-preview/frame.js (frame opening 300 x 400 mm for A4,
  // 400 x 500 mm for A3, 610 x 762 mm for 18 x 24 in; the mat hides 5 mm of the print on each side). Confirm with your framer.
  mat: { name: "Off-white mat", price: { a4: 299, a3: 399, "18x24": 599 }, spec: "Off-white mat with a 45\u00b0 bevel, so the thin lines have some space." },

  // Colour themes: bg = background, line = streets AND text. Every pair clears 4.5:1 contrast.
  // Minor roads and water are derived at render time (see data/layout.json "mix"), never stored here.
  themes: [
    { id: "blue",       name: "Gali Blue",   bg: "#3F6BA8", line: "#FFFFFF" },
    { id: "dark-gold",  name: "Dark & Gold", bg: "#14161A", line: "#C9A35B" },
    { id: "cream",      name: "Cream & Ink", bg: "#F2ECE0", line: "#1C1C1C" },
    { id: "forest",     name: "Forest",      bg: "#23392E", line: "#E6DFC8" },
    { id: "blush",      name: "Blush",       bg: "#EED9D2", line: "#5A2F2C" },
    { id: "midnight",   name: "Midnight",    bg: "#0F1B2D", line: "#D8DEE8" },
    { id: "terracotta", name: "Terracotta",  bg: "#A64E33", line: "#FBEFE3" },
    { id: "mono",       name: "Mono Grey",   bg: "#D9D9D6", line: "#2B2B2B" }
  ],

  // Map editions: which year's street network the poster shows. Steps of 25 years from 1920, then 2025 (the current map).
  // density only drives the placeholder preview (older = smaller, sparser city); it is not real data.
  eras: [
    { id: "1920", year: 1920, density: 0.25 },
    { id: "1945", year: 1945, density: 0.4 },
    { id: "1970", year: 1970, density: 0.6 },
    { id: "1995", year: 1995, density: 0.8 },
    { id: "2025", year: 2025, density: 1 }
  ],
  eraNote: "The 1995 map shows today's streets inside the area Delhi had built up by 1995. Earlier years aren't ready yet.",

  // Then & now set: an older year plus the matching 2025 poster, for this much off the two-poster price.
  pairDiscount: 0.15,

  // Personalisation. Orders are fulfilled by hand: these choices are sent with the order and we confirm with a proof.
  areas: [
    { id: "city",   label: "Whole city" },
    { id: "area",   label: "Neighbourhood (about 5 km across)" },
    { id: "street", label: "Street level (about 2 km across)" }
  ],
  marks: [
    { id: "none",  label: "None" },
    { id: "dot",   label: "Dot" },
    { id: "ring",  label: "Ring" },
    { id: "heart", label: "Heart" }
  ],

  defaults: { city: "delhi", theme: "blue", size: "a3", era: "2025", frame: "none" }
};
