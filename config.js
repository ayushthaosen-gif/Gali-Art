/*
 * Gali — single configuration file.
 * Rename the brand, change prices, set the form endpoint or payment link here.
 * Nothing in this file is secret: it is shipped to every visitor's browser.
 * Never put API keys or private tokens here.
 */
window.GALI_CONFIG = {
  brand: {
    name: "Gali", // placeholder brand name — change here only
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

  // seed makes each city's placeholder pattern different. Only Delhi is a real product for now.
  cities: [
  { id: "delhi",   name: "Delhi",   seed: 11, region: "India", lat: 28.6139, lon: 77.2090,
    maps: { "1995": "assets/delhi-1995-lines.webp", "2025": "assets/delhi-lines.webp" } },
    { id: "mumbai", name: "Mumbai", seed: 20, region: "India", lat: 19.076, lon: 72.8777,
      maps: { "2025": "assets/mumbai-lines.webp" } },
    { id: "kolkata", name: "Kolkata", seed: 21, region: "India", lat: 22.5726, lon: 88.3639,
      maps: { "2025": "assets/kolkata-lines.webp" } },
    { id: "panaji", name: "Panaji", seed: 60, region: "India", lat: 15.4909, lon: 73.8278,
      maps: { "2025": "assets/panaji-lines.webp" } }
  ],

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
  eraNote: "1995 shows today's streets within Delhi's 1995 built-up area. Earlier years are coming soon.",

  defaults: { city: "delhi", theme: "blue", size: "a3", era: "2025" }
};
