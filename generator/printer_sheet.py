"""Make the one-sheet specification you hand to a print shop.

  python printer_sheet.py                       # ../print-files/printer-sheet.pdf, lists the test files in ../print-tests
  python printer_sheet.py --out sheet.pdf --contact "Your name, email, phone"

Every number comes from the same files the posters use (data/layout.json, THEMES in make_poster.py), so the sheet cannot
drift from what the generator produces. The paper and finish lines are questions for the printer, not claims.
"""
import argparse
import json
import re
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle
from reportlab.lib.units import mm
from reportlab.platypus import KeepTogether, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from tool import THEMES

HERE = Path(__file__).resolve().parent
L = json.loads((HERE.parent / "data" / "layout.json").read_text(encoding="utf-8"))
BLEED = L["bleed_mm"]
SIZES = [("A4", 210.0, 297.0), ("A3", 297.0, 420.0), ("18 x 24 in", 457.2, 609.6)]
SIZE_BY_ID = dict(zip(["a4", "a3", "18x24"], SIZES))
NAMES = {"blue": "Gali Blue", "dark-gold": "Dark & Gold", "cream": "Cream & Ink", "forest": "Forest", "blush": "Blush",
         "midnight": "Midnight", "terracotta": "Terracotta", "mono": "Mono Grey"}
BLUE = colors.HexColor("#2c4f82")
INK = colors.HexColor("#14213a")
GREY = colors.HexColor("#4a5670")
RULE = colors.HexColor("#d9e1ee")

H1 = ParagraphStyle("h1", fontName="Helvetica-Bold", fontSize=20, leading=24, textColor=INK, spaceAfter=2)
SUB = ParagraphStyle("sub", fontName="Helvetica", fontSize=10, leading=13, textColor=GREY, spaceAfter=8)
H2 = ParagraphStyle("h2", fontName="Helvetica-Bold", fontSize=11.5, leading=14, textColor=BLUE, spaceBefore=11, spaceAfter=4)
P = ParagraphStyle("p", fontName="Helvetica", fontSize=9.2, leading=12.4, textColor=INK)
LI = ParagraphStyle("li", parent=P, leftIndent=11, bulletIndent=0, spaceAfter=2)
CELL = ParagraphStyle("cell", parent=P, fontSize=8.6, leading=11)
HEAD = ParagraphStyle("head", parent=CELL, fontName="Helvetica-Bold", textColor=colors.white)


def bullets(items):
    return [Paragraph(t, LI, bulletText="•") for t in items]


def table(rows, widths, head=True, zebra=True):
    data = [[Paragraph(str(c), HEAD if head and i == 0 else CELL) for c in r] for i, r in enumerate(rows)]
    t = Table(data, colWidths=[w * mm for w in widths], repeatRows=1 if head else 0)
    st = [("VALIGN", (0, 0), (-1, -1), "TOP"), ("LINEBELOW", (0, 0), (-1, -1), 0.4, RULE),
          ("TOPPADDING", (0, 0), (-1, -1), 3), ("BOTTOMPADDING", (0, 0), (-1, -1), 3)]
    if head:
        st.append(("BACKGROUND", (0, 0), (-1, 0), BLUE))
    if zebra:
        st += [("BACKGROUND", (0, i), (-1, i), colors.HexColor("#f7f9fc")) for i in range(2, len(rows), 2)]
    t.setStyle(TableStyle(st))
    return t


def px(mm_, dpi=300):
    return round(mm_ / 25.4 * dpi)


def swatches():
    ids = list(THEMES)
    # a coloured chip with the line colour on it, then the caption under it, two rows of four themes
    data, st2 = [], [("VALIGN", (0, 0), (-1, -1), "TOP"), ("TOPPADDING", (0, 0), (-1, -1), 0), ("BOTTOMPADDING", (0, 0), (-1, -1), 2), ("LEFTPADDING", (0, 0), (-1, -1), 0), ("RIGHTPADDING", (0, 0), (-1, -1), 5)]
    for r in range(2):
        chips, caps = [], []
        for c in range(4):
            tid = ids[r * 4 + c]
            t = THEMES[tid]
            chips.append(Paragraph(f'<font color="{t["line"]}" size="13"><b>&nbsp;G A L I</b></font>', ParagraphStyle("c", parent=CELL, leading=26)))
            caps.append(Paragraph(f'<b>{NAMES[tid]}</b><br/>{t["bg"].upper()} + {t["line"].upper()}', ParagraphStyle("k", parent=CELL, fontSize=7.8, leading=9.6)))
            st2.append(("BACKGROUND", (c, r * 2), (c, r * 2), colors.HexColor(t["bg"])))
        data += [chips, caps]
    tb = Table(data, colWidths=[44.5 * mm] * 4)
    tb.setStyle(TableStyle(st2))
    return tb


def build(out, files, contact):
    doc = SimpleDocTemplate(str(out), pagesize=A4, leftMargin=16 * mm, rightMargin=16 * mm, topMargin=14 * mm, bottomMargin=14 * mm,
                            title="Gali print specification", author="Gali")
    s = [Paragraph("Gali. Print specification", H1),
         Paragraph("Custom city street-map posters. These are test prints to check print quality before a real run. "
                   "Please read the notes on thin lines and colour first: they are where a print can go wrong.", SUB)]

    s.append(Paragraph("1. This job", H2))
    rows = [["File", "Finished size", "Page size in the file", "Colours", "Qty"]]
    for name, size, theme in files:
        _, w, h = SIZE_BY_ID[size]
        rows.append([name, f"{w:g} x {h:g} mm", f"{w + 2 * BLEED:g} x {h + 2 * BLEED:g} mm", NAMES.get(theme, theme), "1"])
    s.append(table(rows, [66, 32, 36, 30, 10]))

    s.append(Paragraph("2. Files and sizes", H2))
    rows = [["Size", "Finished (trim) size", f"File size with {BLEED:g} mm bleed", "Pixels of the PNG at 300 dpi"]]
    for n, w, h in SIZES:
        rows.append([n, f"{w:g} x {h:g} mm", f"{w + 2 * BLEED:g} x {h + 2 * BLEED:g} mm", f"about {px(w + 2 * BLEED)} x {px(h + 2 * BLEED)}"])
    s.append(table(rows, [28, 44, 52, 50]))
    s += bullets([
        "Use the <b>PDF</b> as the master. It is vector, at the exact page size. The PNG is the same artwork at 300 dpi for a proof or if your RIP prefers raster.",
        f"The <b>background colour fills the {BLEED:g} mm bleed</b> on all four sides. There are <b>no crop marks</b>. Trim {BLEED:g} mm from every edge to get the finished size.",
        "<b>Print at 100%.</b> Do not fit to page, scale, rotate, sharpen, or apply auto-enhance or auto-colour. Keep the files as supplied.",
        "Text and the map stay at least 5% of the poster width inside the trim, so a small trim error will not cut into them.",
    ])

    s.append(Paragraph("3. Thin lines: the main thing to check", H2))
    W = lambda w_mm, k: L["roads"][k] * w_mm
    rows = [["Street type", "A4 line width", "A3 line width", "18 x 24 in line width"]]
    for label, k in [("Main roads", "t1"), ("Large streets", "t2"), ("Streets", "t3"), ("Small streets", "t4"), ("Smallest lanes", "t5")]:
        vals = [max(W(w, k), 0.25 * 25.4 / 72) for _, w, _ in SIZES]
        rows.append([label] + [f"{v:.2f} mm ({v * 72 / 25.4:.2f} pt)" for v in vals])
    s.append(table(rows, [40, 42, 42, 50]))
    s += bullets([
        "Lines are never thinner than 0.25 pt (0.09 mm). That is hairline territory, so they need a sharp, high-resolution print.",
        "On <b>Gali Blue and the dark themes the lines are light on a dark colour</b> (knocked out of a solid). Thin knocked-out lines can fill in with ink spread. This is the likeliest problem, so look at the lanes in dense areas of the proof.",
        "On the light themes (Cream, Blush, Mono) the lines are dark on a light colour. These usually print crisper but can look slightly heavier.",
    ])

    s.append(Paragraph("4. Colours", H2))
    s.append(Paragraph("The files are built in screen colours (hex values below). Please convert to your press profile and show a <b>proof before the run</b>. "
                       "<b>Gali Blue #3F6BA8</b> is the brand colour and matters most. Large flat areas of colour should look even, with no banding or streaks.", P))
    s.append(Spacer(1, 4))
    s.append(swatches())

    rows = [["Text", "A4", "A3", "18 x 24 in"]]
    for label, k in [("Line under the title (region)", "region"), ("Coordinates and year", "coords"), ("Optional detail line", "detail")]:
        rows.append([label] + [f"{L[k]['size'] * w / 25.4 * 72:.1f} pt" for _, w, _ in SIZES])
    rows.append(["Title (city name)"] + [f"{L['city']['size'] * w / 25.4 * 72:.0f} pt" for _, w, _ in SIZES])
    s.append(KeepTogether([Paragraph("5. Smallest text on the poster", H2), table(rows, [76, 28, 28, 42])]))

    checks = ["The blue (or the colour of each poster) matches the swatch and looks the same across the whole sheet.",
              "Thin streets in dense areas stay separate and do not clog or break up.",
              "The small footer text (coordinates, year, detail line) is sharp and readable.",
              "The background colour reaches every edge after trimming, with no white sliver.",
              "Cut size is exact, and the title sits centred with equal space left and right."]
    box = ParagraphStyle("box", parent=P, leftIndent=18, firstLineIndent=-18, spaceAfter=3)
    s.append(KeepTogether([Paragraph("6. What to check on the proof", H2)] + [Paragraph("[&nbsp;&nbsp;&nbsp;]&nbsp;&nbsp;" + c, box) for c in checks]))

    s.append(KeepTogether([Paragraph("7. Please tell us", H2),
                           table([["Paper (name and weight)", ""], ["Finish (matte, silk, other)", ""], ["Your CMYK or Pantone match for #3F6BA8", ""],
                                  ["Price per piece and for 10", ""], ["Turnaround", ""], ["Anything in the file you would change", ""]],
                                 [74, 102], head=False, zebra=False)]))
    s.append(Spacer(1, 6))
    s.append(Paragraph(f"Contact: {contact}", P))
    doc.build(s)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(HERE.parent / "print-files" / "printer-sheet.pdf"))
    ap.add_argument("--tests", default=str(HERE.parent / "print-tests"), help="Folder of finished print files to list as this job")
    ap.add_argument("--contact", default="______________________________________________")
    args = ap.parse_args()
    files = []
    for f in sorted(Path(args.tests).glob("*.pdf")):
        m = re.search(r"-\d{4}-([a-z-]+)-(a4|a3|18x24)\.pdf$", f.name)
        if m:
            files.append((f.name, m.group(2), m.group(1)))
    Path(args.out).parent.mkdir(parents=True, exist_ok=True)
    build(args.out, files, args.contact)
    print(f"{args.out}: {len(files)} files listed")


if __name__ == "__main__":
    main()
