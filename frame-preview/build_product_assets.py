"""Make exact print-detail and dimension assets without network or AI artwork.

python build_product_assets.py --source path/to/delhi-2025-blue-a3.png
Requires Pillow in the development environment, not in the static website.
"""
import argparse
import hashlib
import json
from pathlib import Path

from PIL import Image

HERE = Path(__file__).resolve().parent
PRINTS = {"A4": (210, 297), "A3": (297, 420), "18 × 24 in": (457, 610)}


def scale_svg():
    parts = ['<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 2400 1800" width="1600" height="1200" role="img" aria-labelledby="title desc">',
             '<title id="title">A4, A3 and 18 by 24 inch prints above a 180 centimetre sofa</title>',
             '<desc id="desc">Print rectangles are drawn at one shared scale using their millimetre dimensions. The sofa outline is an illustrative 1800 millimetre wide reference. Frames and mats are excluded.</desc>',
             '<rect width="2400" height="1800" fill="#E6E1D8"/>',
             '<g font-family="Arial,sans-serif" fill="#343A30" text-anchor="middle">']
    for centre, (name, (width, height)) in zip((650, 1200, 1750), PRINTS.items()):
        x, y = centre - width / 2, 700 - height
        parts.extend([f'<rect x="{x}" y="{y}" width="{width}" height="{height}" fill="#3F6BA8"/>',
                      f'<text x="{centre}" y="{700 - width * .12}" fill="white" font-size="{width * .072}" letter-spacing="{width * .015}">DELHI</text>',
                      f'<text x="{centre}" y="760" font-size="36">{name}</text>',
                      f'<text x="{centre}" y="810" font-size="28" fill="#6F7366">{width} × {height} mm</text>'])
    parts.extend(['</g>',
                  '<g fill="none" stroke="#7C8073" stroke-width="5" stroke-linejoin="round">',
                  '<path d="M380 1110V915Q380 850 450 850H1950Q2020 850 2020 915V1110"/>',
                  '<path d="M300 1430V1130Q300 1100 330 1100H405Q435 1100 435 1130V1370H1965V1130Q1965 1100 1995 1100H2070Q2100 1100 2100 1130V1430Z"/>',
                  '<path d="M435 1220H1965M1200 870V1210M460 1240H1180V1350H460ZM1220 1240H1940V1350H1220Z"/>',
                  '<path d="M350 1430V1600H395V1430M2005 1430V1600H2050V1430"/>',
                  '<path d="M220 1600H2180" stroke="#C0C0B3"/>',
                  '<path d="M300 1680H2100M300 1655V1705M2100 1655V1705"/>',
                  '</g><text x="1200" y="1750" text-anchor="middle" fill="#63695C" font-family="Arial,sans-serif" font-size="28" letter-spacing="3">REFERENCE SOFA · 180 CM WIDE</text></svg>'])
    return "\n".join(parts) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--source", type=Path, required=True)
    parser.add_argument("--crop", type=int, nargs=4, default=[1350, 1250, 2350, 2100], metavar=("LEFT", "TOP", "RIGHT", "BOTTOM"))
    parser.add_argument("--out", type=Path, default=HERE)
    args = parser.parse_args()
    with Image.open(args.source) as source:
        dpi = source.info.get("dpi", ())
        if len(dpi) != 2 or any(abs(value - 300) > .1 for value in dpi):
            parser.error("Source must be an actual 300 dpi generator PNG")
        left, top, right, bottom = args.crop
        if not (0 <= left < right <= source.width and 0 <= top < bottom <= source.height):
            parser.error("Crop must lie inside the source")
        args.out.mkdir(parents=True, exist_ok=True)
        crop = source.crop(args.crop)
        path = args.out / "delhi-line-detail.png"
        crop.save(path, dpi=(300, 300), optimize=True)
        with Image.open(path) as exported:
            assert exported.mode == crop.mode and exported.size == crop.size
            assert exported.tobytes() == crop.tobytes(), "Crop pixels changed during export"
        web_path = args.out / "delhi-line-detail.webp"
        crop.save(web_path, lossless=True, quality=100, method=6)
        with Image.open(web_path) as exported:
            assert exported.convert("RGBA").tobytes() == crop.convert("RGBA").tobytes(), "WebP pixels changed"
        provenance = {"source_filename": args.source.name, "source_sha256": hashlib.sha256(args.source.read_bytes()).hexdigest(),
                      "source_size_px": list(source.size), "source_dpi": list(dpi), "crop_box_px": args.crop,
                      "crop_size_px": list(crop.size), "crop_size_mm": [round(value / 300 * 25.4, 2) for value in crop.size],
                      "method": "Pixel-exact crop of an existing generator PNG; no resizing, enhancement or AI image generation",
                      "crop_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
                      "web_crop_sha256": hashlib.sha256(web_path.read_bytes()).hexdigest(), "web_encoding": "lossless WebP; decoded RGBA pixels verified identical"}
    (args.out / "detail-provenance.json").write_text(json.dumps(provenance, indent=2) + "\n", encoding="utf-8")
    (args.out / "size-comparison.svg").write_text(scale_svg(), encoding="utf-8")
    print(f"Saved exact {crop.width} × {crop.height} crop at 300 dpi; verified identical pixels")
    print("Saved size-comparison.svg: shared millimetre scale, 1800 mm reference sofa")


if __name__ == "__main__":
    main()
