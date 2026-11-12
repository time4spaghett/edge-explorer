"""BLACKBIRD wordmark as inline SVG (Alex 2026-11-10: "not technobrutalist enough, can you generate smth ... like if
you had a font inspired by the f 117 nighthawk"). Hand-built capitals on a 7 x 10 grid: flat polygons, thick strokes,
cut (chamfered) corners instead of curves, small slit counters, slanted as a whole. No font file involved.
"""
H, W, T, C = 10.0, 7.0, 2.4, 1.6  # cap height, letter width, stroke, chamfer
GAP = 1.3


def _p(pts, dx):
    return "M" + " L".join(f"{x + dx:.2f},{y:.2f}" for x, y in pts) + " Z"


def _letter(ch, dx):
    m = H / 2
    if ch == "B":
        outer = [(0, 0), (W - C, 0), (W, C), (W, m - .9), (W - .9, m), (W, m + .9), (W, H - C), (W - C, H), (0, H)]
        return [_p(outer, dx), _p([(T, T), (W - T, T), (W - T, m - T / 2), (T, m - T / 2)], dx),
                _p([(T, m + T / 2), (W - T, m + T / 2), (W - T, H - T), (T, H - T)], dx)], W
    if ch == "L":
        return [_p([(0, 0), (T, 0), (T, H - T), (W, H - T), (W, H), (C, H), (0, H - C)], dx)], W
    if ch == "A":
        bar = H * .6
        outer = [(0, H), (0, C * 1.4), (C * 1.4, 0), (W - C * 1.4, 0), (W, C * 1.4), (W, H), (W - T, H),
                 (W - T, bar), (T, bar), (T, H)]
        return [_p(outer, dx), _p([(T, T), (W - T, T), (W - T, bar - T), (T, bar - T)], dx)], W
    if ch == "C":
        return [_p([(C, 0), (W, 0), (W, T), (T, T), (T, H - T), (W, H - T), (W, H), (C, H), (0, H - C), (0, C)],
                   dx)], W
    if ch == "K":
        k = 2.7
        return [_p([(0, 0), (T, 0), (T, H), (0, H)], dx),
                _p([(T, m - .2), (W - k, 0), (W, 0), (T + k * .9, m + .2)], dx),
                _p([(T, m - .2), (T + k * .9, m - .2), (W, H), (W - k, H)], dx)], W
    if ch == "I":
        return [_p([(0, 0), (T, 0), (T, H), (0, H)], dx)], T
    if ch == "R":
        bowl = H * .58
        outer = [(0, 0), (W - C, 0), (W, C), (W, bowl - C * .7), (W - C * .7, bowl), (T, bowl), (T, H), (0, H)]
        leg = [(W - T - .6, bowl), (W - .6, bowl), (W, bowl + .8), (W, H), (W - T, H), (W - T, bowl + .8)]
        return [_p(outer, dx), _p([(T, T), (W - T, T), (W - T, bowl - T), (T, bowl - T)], dx), _p(leg, dx)], W
    if ch == "D":
        c2 = C * 1.5
        outer = [(0, 0), (W - c2, 0), (W, c2), (W, H - c2), (W - c2, H), (0, H)]
        return [_p(outer, dx), _p([(T, T), (W - T - .4, T), (W - T, T + .4), (W - T, H - T - .4),
                                   (W - T - .4, H - T), (T, H - T)], dx)], W
    raise ValueError(ch)


def svg(text="BLACKBIRD", height=54, colour="#FFFFFF"):
    paths, x = [], 0.0
    for ch in text:
        ps, w = _letter(ch, x)
        paths += ps
        x += w + GAP
    width = x - GAP + 3  # room for the slant
    d = " ".join(paths)
    return (f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="-1 -0.5 {width:.1f} {H + 1}" height="{height}" '
            f'style="display:inline-block;vertical-align:baseline" role="img" aria-label="{text}">'
            f'<g transform="skewX(-14) translate(2.4,0)"><path fill="{colour}" fill-rule="evenodd" d="{d}"/></g></svg>')


if __name__ == "__main__":
    from pathlib import Path
    Path("wordmark_preview.svg").write_text(svg(), encoding="utf-8")
    print("wrote wordmark_preview.svg")
