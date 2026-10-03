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
    { id: "delhi",   name: "Delhi",   seed: 11 },
    { id: "mumbai",  name: "Mumbai",  seed: 23, soon: true },
    { id: "kolkata", name: "Kolkata", seed: 37, soon: true }
  ],

  // Colour themes: bg = background, line = street colour.
  themes: [
    { id: "blue",       name: "Gali Blue",   bg: "#3F6BA8", line: "#FFFFFF" },
    { id: "dark-gold",  name: "Dark & Gold", bg: "#111418", line: "#C9A24B" },
    { id: "cream",      name: "Cream & Ink", bg: "#F3ECDD", line: "#1B1B1B" },
    { id: "forest",     name: "Forest",      bg: "#1F4D3A", line: "#EAF2E3" },
    { id: "blush",      name: "Blush",       bg: "#F2D7D5", line: "#7A2E3A" },
    { id: "midnight",   name: "Midnight",    bg: "#0B1D3A", line: "#9FD0FF" },
    { id: "terracotta", name: "Terracotta",  bg: "#B9553A", line: "#FFF1E0" },
    { id: "mono",       name: "Mono Grey",   bg: "#E4E4E4", line: "#222222" }
  ],

  defaults: { city: "delhi", theme: "blue", size: "a3" }
};
