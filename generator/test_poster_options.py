"""Offline checks for the personalisation options (detail line, edition, marker). Run: python test_poster_options.py"""
import subprocess
import sys
import tempfile
from pathlib import Path

from PIL import Image, ImageChops

import make_poster as mp

HERE = Path(__file__).resolve().parent


def run(extra, out):
    cmd = [sys.executable, str(HERE / "make_poster.py"), "--preview", "--size", "a4", "--dpi", "60",
           "--formats", "png", "--out", str(out)] + extra
    res = subprocess.run(cmd, capture_output=True, text=True, cwd=HERE)
    assert res.returncode == 0, res.stderr[-600:]
    return Image.open(next(Path(out).glob("*.png"))).convert("RGB"), res.stdout


def main():
    L = mp.load_layout()
    texts = {"city": "Delhi", "region": "India", "year": 1995, "coords": "28.6139° N, 77.2090° E",
             "date": "14 FEB 2026", "detail": "Where we met", "edition": "NO. 14 / 100"}
    lines, _ = mp.footer_lines(L, 595.0, 842.0, texts)
    order = [ln["text"] for ln in lines]  # bottom to top
    assert order[:4] == ["Where we met", "NO. 14 / 100", "14 FEB 2026", "1995"], order
    assert mp.fmt_edition("14/100") == "NO. 14 / 100" and mp.fmt_edition("founder") == "FOUNDER"
    assert lines[-1]["base"] > 0 and all(a["base"] > b["base"] for a, b in zip(lines, lines[1:])), "lines must stack upward"

    with tempfile.TemporaryDirectory() as d:
        base, _ = run([], Path(d) / "a")
        decorated, out = run(["--detail", "Where we met", "--edition", "14/100", "--mark", "28.6129", "77.2295",
                              "--mark-style", "heart"], Path(d) / "b")
        assert base.size == decorated.size
        assert ImageChops.difference(base, decorated).getbbox() is not None, "options changed nothing"
        _, warn = run(["--city-name", "दिल्ली"], Path(d) / "c")
        assert "non-Latin" in warn, "script warning missing"
        far, warn2 = run(["--mark", "10", "10"], Path(d) / "e")
        assert "outside the mapped area" in warn2
    print("Personalisation option tests passed")


if __name__ == "__main__":
    main()
