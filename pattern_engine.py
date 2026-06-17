"""Deterministic image-to-triangular-panel pattern engine."""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable

import numpy as np
from PIL import Image, ImageDraw

from facade_layout import Panel, Rect, triangle_points
from palette import DEFAULT_BOTTOM_TRIM, DEFAULT_TOP_TRIM, PALETTE, SPECIAL_COLORS, WINDOW_COLOR

DARK_NAMES = ("DEEP BLUE", "BLACK CLEAR", "ANTHRACITE", "BLACK ACID", "GREY")


def hex_to_rgb(hex_color: str) -> np.ndarray:
    h = hex_color.lstrip("#")
    return np.array([int(h[i:i + 2], 16) for i in (0, 2, 4)], dtype=np.float32)


def rgb_to_hex(rgb: Iterable[int]) -> str:
    r, g, b = [int(v) for v in rgb]
    return f"#{r:02X}{g:02X}{b:02X}"


def usable_palette(accent_limit: int, palette: Dict[str, str] | None = None,
                   enabled_colors: Iterable[str] | None = None) -> Dict[str, str]:
    """Return the enabled manufacturer palette constrained by accent color limit."""
    palette = palette or PALETTE
    if enabled_colors is not None:
        names = [name for name in enabled_colors if name in palette]
    else:
        names = list(palette)
    # Keep a stable neutral/core set, then allow a bounded number of warmer accents.
    core = [n for n in names if n not in {"CORAL BROWN", "CLAY", "CORTEN STEEL", "OCHER", "SAND", "TERRACOTTA"}]
    accents = [n for n in names if n not in core][: max(0, accent_limit)]
    selected = core + accents
    return {n: palette[n] for n in selected} or dict(palette)

def nearest_palette_color(rgb: np.ndarray, palette: Dict[str, str]) -> tuple[str, str, float]:
    best_name, best_hex, best_dist = "", "#000000", float("inf")
    for name, hex_color in palette.items():
        if name == WINDOW_COLOR:
            continue
        dist = float(np.sum((rgb - hex_to_rgb(hex_color)) ** 2))
        if dist < best_dist:
            best_name, best_hex, best_dist = name, hex_color, dist
    return best_name, best_hex, best_dist


def _polygon_mask(size: tuple[int, int], points: list[tuple[float, float]]) -> np.ndarray:
    mask = Image.new("L", size, 0)
    ImageDraw.Draw(mask).polygon(points, fill=255)
    return np.asarray(mask) > 0


def _sample_polygon(image: Image.Image, points: list[tuple[float, float]]) -> np.ndarray:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    mask = _polygon_mask(image.size, points)
    if not mask.any():
        return arr.mean(axis=(0, 1))
    return arr[mask].mean(axis=0)


def _score_polygon(image: Image.Image, points: list[tuple[float, float]], color_hex: str) -> float:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    mask = _polygon_mask(image.size, points)
    if not mask.any():
        return 0.0
    color = hex_to_rgb(color_hex)
    return float(np.mean(np.sum((arr[mask] - color) ** 2, axis=1)))


def _apply_gradient(rgb: np.ndarray, rect: Rect, total_height: float, strength: float) -> np.ndarray:
    if strength <= 0:
        return rgb
    y_norm = (rect.y + rect.height / 2) / total_height
    dark = hex_to_rgb(PALETTE["DEEP BLUE"])
    light = hex_to_rgb(PALETTE["POLAR WHITE"])
    target = dark * y_norm + light * (1 - y_norm)
    return rgb * (1 - strength) + target * strength


def _pick_full_panel(image: Image.Image, panel: Panel, palette: Dict[str, str], rng: np.random.Generator,
                     diagonal_randomness: float, gradient_strength: float) -> Panel:
    choices = []
    for split in ("TL_BR", "BL_TR"):
        a_pts, b_pts = triangle_points(panel.rect, split)
        a_rgb = _apply_gradient(_sample_polygon(image, a_pts), panel.rect, image.height, gradient_strength)
        b_rgb = _apply_gradient(_sample_polygon(image, b_pts), panel.rect, image.height, gradient_strength)
        a_name, a_hex, _ = nearest_palette_color(a_rgb, palette)
        b_name, b_hex, _ = nearest_palette_color(b_rgb, palette)
        score = _score_polygon(image, a_pts, a_hex) + _score_polygon(image, b_pts, b_hex)
        if diagonal_randomness > 0:
            score += rng.normal(0, diagonal_randomness * 5000)
        choices.append((score, split, a_name, a_hex, b_name, b_hex))
    _, split, a_name, a_hex, b_name, b_hex = min(choices, key=lambda item: item[0])
    return replace(panel, split_direction=split, triangle_a_color_name=a_name, triangle_a_hex=a_hex,
                   triangle_b_color_name=b_name, triangle_b_hex=b_hex)


def _apply_symmetry(full_panels: list[Panel], columns: int, mode: str, repeat_n: int) -> list[Panel]:
    by_key = {(p.row, p.col): p for p in full_panels}
    out = []
    for p in full_panels:
        src_col = p.col
        if mode == "mirror around center":
            src_col = min(p.col, columns - 1 - p.col)
        elif mode == "repeat every N bays" and repeat_n > 0:
            src_col = p.col % repeat_n
        src = by_key.get((p.row, src_col), p)
        out.append(replace(p, split_direction=src.split_direction,
                           triangle_a_color_name=src.triangle_a_color_name, triangle_a_hex=src.triangle_a_hex,
                           triangle_b_color_name=src.triangle_b_color_name, triangle_b_hex=src.triangle_b_hex))
    return out


def _apply_sail_motif(full_panels: list[Panel], columns: int, seed: int, palette: Dict[str, str]) -> list[Panel]:
    rng = np.random.default_rng(seed + 991)
    darks = [n for n in DARK_NAMES if n in palette]
    if not darks:
        return full_panels
    out = []
    centers = {int(rng.integers(0, max(columns, 1))) for _ in range(max(1, columns // 4))}
    for p in full_panels:
        near = any(abs(p.col - c) <= max(0, 1 - p.row // 2) for c in centers)
        if near and rng.random() < 0.75:
            name = darks[(p.row + p.col) % len(darks)]
            hx = palette[name]
            # Preserve two triangles; bias one or both toward dark sail colors.
            if p.row == 1:
                out.append(replace(p, triangle_a_color_name=name, triangle_a_hex=hx, triangle_b_color_name=name, triangle_b_hex=hx))
            else:
                out.append(replace(p, triangle_a_color_name=name, triangle_a_hex=hx))
        else:
            out.append(p)
    return out


def generate_pattern(layout: list[Panel], reference: Image.Image, columns: int, accent_limit: int = 3,
                     symmetry_mode: str = "none", repeat_n: int = 4, seed: int = 0,
                     diagonal_randomness: float = 0.0, gradient_strength: float = 0.0,
                     sail_motif: bool = False, top_trim: str = DEFAULT_TOP_TRIM,
                     bottom_trim: str = DEFAULT_BOTTOM_TRIM, palette: Dict[str, str] | None = None,
                     enabled_palette_colors: Iterable[str] | None = None,
                     window_glass_color: str | None = None) -> list[Panel]:
    """Assign split directions and palette colors to all layout panels."""
    rng = np.random.default_rng(seed)
    facade_w = int(max(p.rect.x2 for p in layout))
    facade_h = int(max(p.rect.y2 for p in layout))
    image = reference.convert("RGB").resize((facade_w, facade_h), Image.Resampling.LANCZOS)
    palette = palette or PALETTE
    pal = usable_palette(accent_limit, palette, enabled_palette_colors)

    full = [_pick_full_panel(image, p, pal, rng, diagonal_randomness, gradient_strength) for p in layout if p.panel_type == "full"]
    full = _apply_symmetry(full, columns, symmetry_mode, repeat_n)
    if sail_motif:
        full = _apply_sail_motif(full, columns, seed, pal)
    full_by_key = {(p.row, p.col): p for p in full}

    result = []
    for p in layout:
        if p.panel_type == "full":
            result.append(full_by_key[(p.row, p.col)])
        elif p.panel_type == "window":
            hx = window_glass_color or SPECIAL_COLORS[WINDOW_COLOR]
            result.append(replace(p, triangle_a_color_name=WINDOW_COLOR, triangle_a_hex=hx,
                                  triangle_b_color_name=WINDOW_COLOR, triangle_b_hex=hx))
        elif p.panel_type == "dummy":
            neighbor_col = p.col - 1 if p.side == "L" else p.col + 1
            inherited = full_by_key.get((p.row, neighbor_col)) or full_by_key.get((p.row - 1, p.col)) or full_by_key.get((p.row + 1, p.col))
            name = inherited.triangle_a_color_name if inherited else "DEEP BLUE"
            hx = inherited.triangle_a_hex if inherited else palette["DEEP BLUE"]
            result.append(replace(p, triangle_a_color_name=name, triangle_a_hex=hx, triangle_b_color_name=name, triangle_b_hex=hx))
        elif p.panel_type in {"top_trim", "bottom_trim", "trim"}:
            name = top_trim if p.panel_id == "T_TOP" else bottom_trim
            color_lookup = {**palette, **SPECIAL_COLORS}
            hx = color_lookup.get(name, name if str(name).startswith("#") else SPECIAL_COLORS[DEFAULT_TOP_TRIM])
            result.append(replace(p, triangle_a_color_name=name, triangle_a_hex=hx, triangle_b_color_name=name, triangle_b_hex=hx))
    return result
