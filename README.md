# Gali

Static site for a custom city street-map poster business. First product: Delhi, white streets on solid blue (`#3F6BA8`), no labels. "Gali" is a placeholder brand name.

Plain HTML, CSS and vanilla JS. No framework, no build step, relative paths only, so it runs at any domain or subpath.

## Structure

```
index.html            landing page (hero, how it works, gallery, style picker, order form, FAQ)
404.html, privacy.html
config.js             ALL configuration: brand, email, form endpoint, payment link, prices, themes
css/style.css
js/poster.js          placeholder SVG street-pattern renderer
js/app.js             picker, gallery, order form
data/posters.json     gallery items (swap in real images here)
data/layout.json      poster layout (fractions of width), shared by the website and the generator
assets/               images, favicon
generator/            Python script that renders real maps (run locally/Colab)
.github/workflows/pages.yml
```

## Run locally

Quick look: open `index.html` in a browser. The gallery will use a fallback, because browsers block `fetch` of local files.

Full behaviour: serve the folder.

```bash
python3 -m http.server 8000
# open http://localhost:8000  (on your phone: http://<your-computer-ip>:8000 on the same Wi-Fi)
```

## Configure

Everything is in `config.js`:

- `brand.name` — rename the brand here (and nowhere else). `brand.email` — contact address.
- `form.endpoint` — Formspree URL (`mode: "json"`) or Google Apps Script web-app URL (`mode: "no-cors"`). Empty = demo mode, nothing is sent.
- `payment.link` — paste a Razorpay/Stripe payment link; shown after a successful request. No payment code exists.
- `sizes[].price`, `currency`, `cities` (name, region, lat/lon shown on the poster), `themes`, `eras` (map years offered).

Never put secrets in `config.js`: it is public. Payment links and form endpoints are public by design.

### Real maps in the live preview
Delhi 2025 uses `assets/delhi-lines.webp`, a white-lines-on-transparent image the site recolours for every theme. For another city or year, make a mask with `generator/make_poster.py --formats mask` (see its README), put it in `assets/`, and add it under that city's `maps` in `config.js` (`maps: { "<year>": "assets/..." }`). Without an entry the site shows the generated placeholder pattern.

### Real poster images

1. Generate with `generator/` (see its README) into `assets/`.
2. In `data/posters.json`, set `"image": "assets/delhi-2025-blue-a3.png"` and a descriptive `"alt"`.

## Deploy to GitHub Pages

1. Push to `main`.
2. Repo **Settings → Pages → Source: GitHub Actions**.
3. The workflow in `.github/workflows/pages.yml` publishes on each push to `main` (or run it manually from the Actions tab).

Site URL will be `https://<user>.github.io/<repo>/`. Nothing in the code depends on that.

## Migrate to Cloudflare Pages or Netlify

No build step, so setup is trivial.

**Cloudflare Pages**
1. Dashboard → Workers & Pages → Create → Pages → Connect to Git → pick the repo.
2. Framework preset: *None*. Build command: *(empty)*. Output directory: `/` (repo root).
3. Deploy. You get `<project>.pages.dev`.
4. Custom domain: project → **Custom domains → Set up a domain**, enter e.g. `www.yourdomain.com`. If the domain's DNS is on Cloudflare it adds the record for you; otherwise add the CNAME it shows (to `<project>.pages.dev`) at your registrar.

**Netlify**
1. Add new site → Import from Git → pick the repo.
2. Build command: *(empty)*. Publish directory: `.`.
3. Custom domain: Site configuration → **Domain management → Add a domain**. Either use Netlify DNS (change nameservers) or add a CNAME for `www` to `<site>.netlify.app`.

Notes:
- Root/apex domains need ALIAS/ANAME/CNAME-flattening (Cloudflare does this natively), or A records given by the host. Redirect apex ↔ `www` in the host's settings.
- HTTPS certificates are issued automatically; allow a few minutes after DNS propagates.
- Both hosts serve `404.html` automatically. The `generator/`, `README.md` and `.github/` files will be public on these hosts too; add them to a `.gitignore`d copy or remove them from the publish directory if you'd rather not expose them.
- After moving, you can disable the GitHub Pages workflow.

## Accessibility & performance

Semantic landmarks, skip link, labelled form fields with live error messages, keyboard-focusable theme radios, reduced-motion support, SVG posters with `aria-label`/alt text. No libraries; the page ships a few KB of JS/CSS.
