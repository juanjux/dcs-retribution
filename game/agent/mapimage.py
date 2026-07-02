"""Strategic map PNG for the OPFOR AI, drawn from the same intel views it reads.

The image and the text ``turn_context`` share one source (``build_turn_context``),
so they always agree and the same fog-of-war filter applies. Self-contained PIL
schematic — no satellite tiles, no network — so it renders inside the AI turn loop.
"""

from __future__ import annotations

import io
import math
from typing import Optional

from PIL import Image, ImageDraw, ImageFont

from game.agent import views

_W = _H = 1024
_MARGIN = 70  # px kept clear of the theater bounds (room for edge labels)

_BG = (18, 22, 28)
_GRATICULE = (34, 42, 52)
_LINK = (60, 70, 82)
_BLUE = (70, 140, 240)
_RED = (235, 80, 70)
_NEUTRAL = (140, 140, 140)
_FRONT = (250, 200, 60)
_TEXT = (225, 228, 232)
_TEXT_DIM = (150, 158, 168)


def _font(size: int) -> ImageFont.FreeTypeFont:
    # Pillow >=10 load_default(size) returns a bundled scalable font — no path
    # dependency, so it survives the PyInstaller bundle.
    return ImageFont.load_default(size=size)


def _parse_bbox(bbox: Optional[str]) -> Optional[tuple[float, float, float, float]]:
    if not bbox:
        return None
    try:
        s, w, n, e = (float(v) for v in bbox.split(","))
    except (ValueError, TypeError):
        return None
    if n <= s or e <= w:
        return None
    return s, w, n, e


def render(ctx: views.TurnContextView, bbox: Optional[str] = None) -> bytes:
    pts = [cp.pos for cp in ctx.control_points]
    pts += [t.pos for t in ctx.targets]
    pts += [n.pos for n in ctx.naval]

    box = _parse_bbox(bbox)
    if box is not None:
        min_lat, min_lng, max_lat, max_lng = box
    elif pts:
        lats = [p[0] for p in pts]
        lngs = [p[1] for p in pts]
        min_lat, max_lat = min(lats), max(lats)
        min_lng, max_lng = min(lngs), max(lngs)
    else:
        min_lat, max_lat, min_lng, max_lng = 0.0, 1.0, 0.0, 1.0

    lat_c = (min_lat + max_lat) / 2
    lng_c = (min_lng + max_lng) / 2
    cos_lat = math.cos(math.radians(lat_c)) or 1e-6

    def to_nm(pos: list[float]) -> tuple[float, float]:
        return (pos[1] - lng_c) * 60.0 * cos_lat, (pos[0] - lat_c) * 60.0

    corners = [
        to_nm([min_lat, min_lng]),
        to_nm([max_lat, max_lng]),
    ]
    xs = [c[0] for c in corners]
    ys = [c[1] for c in corners]
    span_x = max(max(xs) - min(xs), 10.0)
    span_y = max(max(ys) - min(ys), 10.0)
    pad_x, pad_y = span_x * 0.06, span_y * 0.06
    min_x, max_x = min(xs) - pad_x, max(xs) + pad_x
    min_y, max_y = min(ys) - pad_y, max(ys) + pad_y
    span_x, span_y = max_x - min_x, max_y - min_y

    scale = min((_W - 2 * _MARGIN) / span_x, (_H - 2 * _MARGIN) / span_y)
    draw_w, draw_h = span_x * scale, span_y * scale
    ox, oy = (_W - draw_w) / 2, (_H - draw_h) / 2

    def to_px(pos: list[float]) -> tuple[float, float]:
        x_nm, y_nm = to_nm(pos)
        return ox + (x_nm - min_x) * scale, oy + (max_y - y_nm) * scale  # north up

    def cp_color(owner: str) -> tuple[int, int, int]:
        return {"red": _RED, "blue": _BLUE}.get(owner, _NEUTRAL)

    base = Image.new("RGBA", (_W, _H), (*_BG, 255))
    d = ImageDraw.Draw(base)

    # Graticule every ~1 degree, labelled at the edges.
    step = 1.0 if (max_lat - min_lat) < 8 else 2.0
    lat = math.ceil(min_lat / step) * step
    while lat <= max_lat:
        _, y = to_px([lat, lng_c])
        d.line([(ox, y), (ox + draw_w, y)], fill=_GRATICULE)
        d.text((6, y - 6), f"{lat:.0f}", font=_font(11), fill=_TEXT_DIM)
        lat += step
    lng = math.ceil(min_lng / step) * step
    while lng <= max_lng:
        x, _ = to_px([lat_c, lng])
        d.line([(x, oy), (x, oy + draw_h)], fill=_GRATICULE)
        d.text((x + 2, _H - 16), f"{lng:.0f}", font=_font(11), fill=_TEXT_DIM)
        lng += step

    cp_by_id = {cp.id: cp for cp in ctx.control_points}

    # Adjacency links between control points (land routes / front seams).
    for cp in ctx.control_points:
        for other in cp.links or []:
            o = cp_by_id.get(other)
            if o and cp.id < other:  # each edge once
                d.line([to_px(cp.pos), to_px(o.pos)], fill=_LINK)

    # Active fronts: a thick line between the two facing control points.
    for t in ctx.targets:
        if t.kind == "front" and t.friendly_cp_id and t.enemy_cp_id:
            f, e = cp_by_id.get(t.friendly_cp_id), cp_by_id.get(t.enemy_cp_id)
            if f and e:
                d.line([to_px(f.pos), to_px(e.pos)], fill=_FRONT, width=3)

    # Threat umbrellas on a translucent overlay so overlaps blend with the map.
    # Ring colour = owner: enemy (blue) SAMs/ships blue, your own naval red.
    overlay = Image.new("RGBA", (_W, _H), (0, 0, 0, 0))
    od = ImageDraw.Draw(overlay)

    def ring(pos: list[float], nm: int, rgb: tuple[int, int, int]) -> None:
        r = nm * scale
        if r < 2:
            return
        x, y = to_px(pos)
        od.ellipse([x - r, y - r, x + r, y + r], fill=(*rgb, 26), outline=(*rgb, 120))

    for t in ctx.targets:
        if t.threat_nm:
            ring(t.pos, t.threat_nm, _BLUE)
    for n in ctx.naval:
        if n.threat_nm:
            ring(n.pos, n.threat_nm, _RED)
    base = Image.alpha_composite(base, overlay)
    d = ImageDraw.Draw(base)

    # Enemy target markers (small): sam triangle, ship square, else dot.
    for t in ctx.targets:
        if t.kind == "front":
            continue
        x, y = to_px(t.pos)
        if t.kind == "ship":
            d.rectangle([x - 3, y - 3, x + 3, y + 3], fill=_BLUE)
        elif t.kind == "sam":
            d.polygon([(x, y - 4), (x - 4, y + 3), (x + 4, y + 3)], fill=_BLUE)
        else:
            d.ellipse([x - 2, y - 2, x + 2, y + 2], fill=_BLUE)

    # Your naval groups: red diamond, with a line to any pending destination.
    for n in ctx.naval:
        x, y = to_px(n.pos)
        if n.destination:
            dx, dy = to_px(n.destination)
            d.line([(x, y), (dx, dy)], fill=_RED, width=1)
            d.polygon(
                [(dx, dy - 4), (dx - 4, dy), (dx, dy + 4), (dx + 4, dy)],
                outline=_RED,
            )
        d.polygon([(x, y - 5), (x - 5, y), (x, y + 5), (x + 5, y)], fill=_RED)

    # Control points on top: filled dot + name.
    f_cp = _font(12)
    for cp in ctx.control_points:
        x, y = to_px(cp.pos)
        c = cp_color(cp.owner)
        d.ellipse([x - 6, y - 6, x + 6, y + 6], fill=c, outline=(240, 240, 240))
        d.text((x + 9, y - 7), cp.name, font=f_cp, fill=_TEXT)

    _draw_chrome(d, ctx, scale)

    buf = io.BytesIO()
    base.convert("RGB").save(buf, "PNG")
    return buf.getvalue()


def _draw_chrome(
    d: ImageDraw.ImageDraw, ctx: views.TurnContextView, scale: float
) -> None:
    """Title, legend, scale bar and north arrow."""
    d.text(
        (10, 8),
        f"OPFOR strategic map - turn {ctx.situation.turn} ({ctx.side} view)",
        font=_font(16),
        fill=_TEXT,
    )

    legend = [
        (_RED, "you (red)"),
        (_BLUE, "enemy (blue)"),
        (_FRONT, "front line"),
        (_NEUTRAL, "neutral"),
    ]
    ly = 30
    for color, label in legend:
        d.rectangle([12, ly + 3, 22, ly + 13], fill=color)
        d.text((28, ly), label, font=_font(12), fill=_TEXT_DIM)
        ly += 18

    # Scale bar: a round-ish nm distance near the bottom-left.
    target_px = 150
    nm = max(round((target_px / scale) / 10) * 10, 10)
    bar = nm * scale
    bx, by = 14, _H - 30
    d.line([(bx, by), (bx + bar, by)], fill=_TEXT, width=2)
    d.line([(bx, by - 4), (bx, by + 4)], fill=_TEXT, width=2)
    d.line([(bx + bar, by - 4), (bx + bar, by + 4)], fill=_TEXT, width=2)
    d.text((bx, by - 18), f"{nm} nm", font=_font(12), fill=_TEXT)

    # North arrow, top-right.
    nx, ny = _W - 26, 40
    d.line([(nx, ny + 14), (nx, ny - 10)], fill=_TEXT, width=2)
    d.polygon([(nx, ny - 16), (nx - 5, ny - 6), (nx + 5, ny - 6)], fill=_TEXT)
    d.text((nx - 4, ny + 16), "N", font=_font(12), fill=_TEXT)
