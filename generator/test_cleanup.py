"""Offline tests for cleanup.py. Run: python test_cleanup.py"""
from cleanup import clip_edges, drop_fragments, promote_names
from make_poster import tier_of


def test_fragments():
    main = [([(0, 0), (300, 0)], "primary"), ([(300, 0), (600, 0)], "primary")]
    speck = [([(5000, 5000), (5100, 5000)], "residential")]
    kept, dropped = drop_fragments(main + speck, 200)
    assert dropped == 1 and len(kept) == 2


def test_clip():
    from shapely.geometry import box
    kept, changed = clip_edges([([(-50, 5), (50, 5)], "primary"), ([(1, 1), (2, 2)], "primary")], box(0, 0, 100, 10))
    assert changed == 1 and kept[0][0] == [(0.0, 5.0), (50.0, 5.0)] and len(kept) == 2


def test_promote():
    out, n = promote_names([([(0, 0), (1, 1)], "tertiary", "Janpath"), ([(0, 0), (1, 1)], "tertiary", "Other Rd"),
                            ([(0, 0), (1, 1)], "motorway", "Janpath")], ["Janpath"], 2, tier_of)
    assert n == 1 and [h for _, h in out] == ["primary", "tertiary", "motorway"]


if __name__ == "__main__":
    test_fragments(); test_clip(); test_promote()
    print("ok")
