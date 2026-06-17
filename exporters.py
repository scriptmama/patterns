"""PNG, SVG, and CSV exporters for facade panels."""
from __future__ import annotations

from io import BytesIO, StringIO

import pandas as pd
import svgwrite
from PIL import Image, ImageDraw

from facade_layout import Panel, triangle_points

STROKE = "#F7FBFC"


def schedule_dataframe(panels: list[Panel], row_mode: str = "3") -> pd.DataFrame:
    rows = []
    for p in panels:
        rows.append({
            "row_mode": str(row_mode),
            "panel_id": p.panel_id,
            "row": p.row,
            "col": p.col + 1,
            "panel_type": p.panel_type,
            "split_direction": p.split_direction,
            "triangle_a_color_name": p.triangle_a_color_name,
            "triangle_a_hex": p.triangle_a_hex,
            "triangle_b_color_name": p.triangle_b_color_name,
            "triangle_b_hex": p.triangle_b_hex,
        })
    return pd.DataFrame(rows)


def export_csv(panels: list[Panel], row_mode: str = "3") -> bytes:
    return schedule_dataframe(panels, row_mode=row_mode).to_csv(index=False).encode("utf-8")


def draw_png(panels: list[Panel], size: tuple[int, int]) -> Image.Image:
    img = Image.new("RGB", size, "white")
    draw = ImageDraw.Draw(img)
    for p in panels:
        r = p.rect
        if p.panel_type == "full":
            a, b = triangle_points(r, p.split_direction)
            draw.polygon(a, fill=p.triangle_a_hex, outline=STROKE)
            draw.polygon(b, fill=p.triangle_b_hex, outline=STROKE)
        else:
            draw.rectangle([r.x, r.y, r.x2, r.y2], fill=p.triangle_a_hex, outline=STROKE)
    return img


def export_png(panels: list[Panel], size: tuple[int, int]) -> bytes:
    buf = BytesIO()
    draw_png(panels, size).save(buf, format="PNG")
    return buf.getvalue()


def export_svg(panels: list[Panel], size: tuple[int, int]) -> bytes:
    dwg = svgwrite.Drawing(size=size, profile="tiny")
    dwg.viewbox(0, 0, size[0], size[1])
    for p in panels:
        r = p.rect
        if p.panel_type == "full":
            a, b = triangle_points(r, p.split_direction)
            dwg.add(dwg.polygon(a, fill=p.triangle_a_hex, stroke=STROKE, stroke_width=1))
            dwg.add(dwg.polygon(b, fill=p.triangle_b_hex, stroke=STROKE, stroke_width=1))
        else:
            dwg.add(dwg.rect(insert=(r.x, r.y), size=(r.width, r.height), fill=p.triangle_a_hex, stroke=STROKE, stroke_width=1))
    return dwg.tostring().encode("utf-8")
