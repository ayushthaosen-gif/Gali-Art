# Live framed-poster preview

Open `index.html` in a modern browser, or serve the repository root and visit `/frame-preview/`. All three finishes start with the Delhi blue poster. The demo uses the existing `../assets/delhi-lines.webp` map mask and HTML typography; it makes no network requests and has no dependencies. Its prices are illustrative INR totals (print + frame + optional mat).

## Add to your site

Copy `frame.css`, `frame.js`, `oak.jpg`, `frame-black.webp`, `frame-oak.webp`, `frame-white.webp` and `wall.jpg` together. Load the CSS and the classic script (optionally with `defer`), then wrap your live poster:

```html
<link rel="stylesheet" href="frame.css">
<div class="frame-wall">
  <div class="framed" data-frame="oak" data-size="A3" data-mat="true">
    <div class="poster">Your existing map and HTML text</div>
  </div>
</div>
<script src="frame.js" defer></script>
```

The existing poster node is moved into a clipping wrapper, preserving references and event listeners. Nothing is rasterised or cloned. Keep your poster's `container-type: inline-size` and `cqw` typography. The `.frame-sheet > .poster` rule supplies full sheet width and height; replace conflicting fixed-size rules in your host stylesheet. Moving the node means selectors such as `.framed > .poster` should instead target `.frame-sheet > .poster`. Host artwork styles remain separate from the frame CSS; the demo's artwork styles live in `index.html` only.

`data-size` accepts `A4`, `A3`, or `18x24`. Frame defaults to black; omitting `data-mat` uses the selected finish's default (oak true, black/white false). Black always forces mat off. Set `data-glazing="ar"` for 30% glare strength. Add `data-tilt="true"` inside a perspective-bearing `.frame-wall` to enable mouse tilt; reduced-motion users get no tilt. Pointer overlays never block the live poster.

Geometry is calculated in millimetres, then scaled by layout width / outer width. A 20 mm face surrounds the opening, and 25 mm depth is represented only by shadow. Without a mat, the opening equals the full print. With a mat, its opening is 300 × 400, 400 × 500 or 610 × 762 mm; the visible window hides 5 mm of the print on each side. The 2.5 mm bevel lies outside that visible window. The full print remains unchanged behind the mat, so container typography is based on full print width. Oak grain is repeated along horizontal pieces and rotated 90° for vertical pieces. White reuses the grain at 6% opacity. Base colours remain visible if a texture fails to load.

Widths default to 70% of the parent, bounded at 280–900 px; at narrower widths the preview shrinks to fit. Override `.framed` width for your layout. The demo compares three cards on wide screens and stacks them below 940 px.

## Photographic materials

All three finishes now use image-generated photographic frame assets with authentic grain, edge highlights, small inner lips and mitred joints. They are 1254 × 1254 lossless WebP files, decoded pixel-for-pixel identical to the original PNGs (RGBA compared, 0 differing values). CSS `border-image` divides each source into four corners and four rails, discarding the entire central image region. Corners stay square at the calculated 20 mm face width; only rails stretch to the current opening. The original poster, mat and glazing remain separate live layers. This also avoids importing any transparency artefacts inside the generated opening.

`FRAMES.photo` selects the asset and `photoSlice` records the source crop in image pixels: 168 for black, 150 for oak and white. These source cuts do not change the millimetre dimensions of the frame. Image load detection activates the photographic layer; the existing CSS frame and oak texture remain as fallbacks if an image is missing. Their drawn seams and arris are hidden after the photograph loads to avoid duplicate details.

`wall.jpg` is an image-generated warm plaster surface with diffuse natural light. `.frame-wall` uses it as a cover background with the original #E6E1D8 fallback. Change that selector to swap the wall or adjust the crop. These are generated material simulations, not photographs of an actual stocked frame product.

## Controls and API

To use the included controls, group each preview and its controls inside `[data-frame-card]`. Copy the demo's controls template: buttons with `data-select-frame`, an input with `data-mat-toggle` inside a label, `data-frame-price`, and `data-frame-note`. Buttons have accessible labels and `aria-pressed`; totals announce changes. The mat label hides for black. A theme identifier on `.poster[data-theme]` (or the `.framed` fallback) drives the white-frame note for cream, blush and mono-grey. Theme recommendations are advisory; every finish remains selectable.

```js
const preview = FramePreview.mount(document.querySelector('.framed'));
preview.set({ frame: 'white', mat: true, size: '18x24', glazing: 'ar' });
preview.poster.querySelector('.city').textContent = 'Delhi'; // use your own selector
preview.poster.dataset.theme = 'cream';
// Direct data-* changes are observed; mounting twice returns the same instance.
```

Changing finish through `set()` or a swatch applies that finish's default mat. Explicit `mat` in the same call takes precedence where allowed. Direct attribute changes retain the current mat unless changed separately. `framechange` bubbles with the current data attributes after `set()`. Dynamically inserted previews need `FramePreview.mount(element)`. `ResizeObserver` recalculates geometry on resize.

## Add a new frame

1. Add an entry to `FRAMES` in `frame.js`: `face` in mm, `color`, `mat`, `matAllowed`, `themes`, and optionally `photo`, `photoSlice`, `texture`, `avoid`, and `label`. Image paths resolve relative to `frame.js`.
2. For a photographic finish, supply a straight-on square frame PNG whose outside edges touch the image bounds. Set `photoSlice` to the distance in source pixels from the outer edge to the inner opening; asymmetric assets can use four values (top/right/bottom/left). The centre is discarded, so never include the poster in the material asset. Optionally supply a seamless 512 × 512 horizontal grain JPEG as a fallback; side pieces rotate it automatically. If the source image is resized, recalibrate its slice values.
3. Add matching per-size prices to `PRICES.frame`. Edit `PRICES.print`, `PRICES.mat`, currency and locale for real pricing.
4. Add a labelled `data-select-frame="your-id"` swatch and its CSS colour/texture. The generic geometry, clipping, lighting and seams work with the new finish. Add a finish-specific CSS selector if it needs a different sheen or texture opacity.

Any additional print size needs entries in both `PRINTS` and `MAT.frames`, matching price keys and a UI option. `FramePreview.geometry(size, frame, mat)` exposes the unscaled mm geometry for inspection. No production website files or layout configuration are changed by this demo.

## Verification

Checked JS syntax and all 18 combinations of size, frame and mat geometry at 280 and 900 px, including outer dimensions and exact 5 mm overlap. Browser checks covered desktop comparison, 320 px mobile reflow without horizontal overflow, A3 and 18 × 24 sizing, frame defaults, mat toggles, price updates, live text, cream-theme advice and anti-reflective glare opacity. The reduced-motion CSS and event guard are included; a browser with an enabled OS reduced-motion preference was not available for that check. This is a material simulation; real frame samples and the production site's renderer/checkout still need integration review.

The photographic update was checked for successful loading of all three sources, correct border-image slices, desktop/mobile presentation, live city/theme editing, A3 resizing and mat controls. Browser error/warning logs were empty during these checks.
