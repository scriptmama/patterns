"""Deterministic image-to-triangular-panel pattern engine."""
from __future__ import annotations

from dataclasses import replace
from typing import Dict, Iterable

import numpy as np
from PIL import Image, ImageDraw, ImageEnhance, ImageOps

from facade_layout import Panel, Rect, triangle_points
from palette import DEFAULT_BOTTOM_TRIM, DEFAULT_TOP_TRIM, PALETTE, PALETTE_GROUPS, SPECIAL_COLORS, WINDOW_COLOR

DARK_NAMES = ("DEEP BLUE", "BLACK CLEAR", "ANTHRACITE", "BLACK ACID", "GREY")

WARM_NAMES = set(PALETTE_GROUPS["warm_accents"])
GREEN_NAMES = set(PALETTE_GROUPS["green_accents"])
LIGHT_NAMES = set(PALETTE_GROUPS["light_field"])
BLUE_NAMES = set(PALETTE_GROUPS["blue_field"])
DARK_SET = set(PALETTE_GROUPS["dark_accents"])


def palette_from_groups(groups: Iterable[str] | None, palette: Dict[str, str] | None = None,
                        enabled_colors: Iterable[str] | None = None) -> Dict[str, str]:
    """Return manufacturer colors allowed by semantic palette groups."""
    palette = palette or PALETTE
    enabled = set(enabled_colors or palette)
    if not groups:
        names = list(enabled)
    else:
        names = []
        for group in groups:
            for name in PALETTE_GROUPS.get(group, []):
                if name in enabled and name not in names:
                    names.append(name)
    return {n: palette[n] for n in names if n in palette} or {n: palette[n] for n in enabled if n in palette} or dict(palette)


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



def _crop_reference(image: Image.Image, crop_mode: str, manual_crop: tuple[float, float, float, float] | None = None) -> Image.Image:
    img = image.convert("RGB")
    w, h = img.size
    if crop_mode == "center crop":
        side = min(w, h)
        return ImageOps.fit(img, (side, side), method=Image.Resampling.LANCZOS, centering=(0.5, 0.5))
    if crop_mode == "manual crop" and manual_crop:
        left, top, right, bottom = manual_crop
        box = (int(w * left), int(h * top), int(w * right), int(h * bottom))
        if box[2] > box[0] and box[3] > box[1]:
            return img.crop(box)
    return img


def _active_motif_crop(image: Image.Image) -> Image.Image:
    arr = np.asarray(image.convert("RGB"), dtype=np.float32)
    if arr.size == 0:
        return image
    diff = np.linalg.norm(arr - np.median(arr.reshape(-1, 3), axis=0), axis=2)
    mask = diff > max(18.0, float(np.percentile(diff, 70)))
    ys, xs = np.where(mask)
    if len(xs) < 10 or len(ys) < 10:
        return image
    pad_x = max(2, int((xs.max() - xs.min()) * 0.08))
    pad_y = max(2, int((ys.max() - ys.min()) * 0.08))
    return image.crop((max(0, xs.min() - pad_x), max(0, ys.min() - pad_y), min(image.width, xs.max() + pad_x), min(image.height, ys.max() + pad_y)))


def prepare_reference_image(reference: Image.Image, size: tuple[int, int], *, mode: str = "Image Sampling",
                            crop_mode: str = "full image", manual_crop: tuple[float, float, float, float] | None = None,
                            x_offset: float = 0.0, y_offset: float = 0.0, scale: float = 1.0,
                            tile_horizontal: bool = False, mirror_tile: bool = False,
                            contrast_boost: float = 1.0, saturation_boost: float = 1.0,
                            posterize_colors: int = 8, motif_grid_cols: int | None = None,
                            motif_grid_rows: int | None = None, active_crop: bool = False) -> Image.Image:
    """Build the reduced image/motif that façade triangles sample."""
    base = _crop_reference(reference, crop_mode, manual_crop)
    if active_crop:
        base = _active_motif_crop(base)
    if mode == "Graphic Motif":
        base = ImageEnhance.Contrast(base).enhance(contrast_boost)
        base = ImageEnhance.Color(base).enhance(saturation_boost)
        colors = max(2, min(32, int(posterize_colors)))
        base = base.convert("P", palette=Image.Palette.ADAPTIVE, colors=colors).convert("RGB")
    w, h = size
    sw, sh = max(1, int(w * max(0.1, scale))), max(1, int(h * max(0.1, scale)))
    fitted = ImageOps.fit(base, (sw, sh), method=Image.Resampling.NEAREST if mode == "Graphic Motif" else Image.Resampling.LANCZOS)
    canvas = Image.new("RGB", size, tuple(np.asarray(fitted).reshape(-1, 3).mean(axis=0).astype(int)))
    ox = int(x_offset * w / 100)
    oy = int(y_offset * h / 100)
    if tile_horizontal:
        x = -sw + (ox % sw)
        i = 0
        while x < w:
            tile = ImageOps.mirror(fitted) if mirror_tile and i % 2 else fitted
            canvas.paste(tile, (x, oy - max(0, (sh - h) // 2)))
            x += sw
            i += 1
    else:
        canvas.paste(fitted, ((w - sw) // 2 + ox, (h - sh) // 2 + oy))
    if mode == "Graphic Motif":
        gc = motif_grid_cols or max(3, w // 80)
        gr = motif_grid_rows or max(3, h // 110)
        small = canvas.resize((gc, gr), Image.Resampling.NEAREST)
        canvas = small.resize(size, Image.Resampling.NEAREST)
    return canvas


def _palette_family_for_rgb(rgb: np.ndarray, palette: Dict[str, str], background_bias: str = "balanced", accent_strength: float = 0.7) -> Dict[str, str]:
    r, g, b = rgb
    brightness = float(np.mean(rgb))
    sat = float(max(rgb) - min(rgb))
    accent_threshold = 55 - 35 * max(0.0, min(1.0, accent_strength))
    if brightness < 70:
        names = DARK_SET
    elif r > g * 1.05 and r > b * 1.15 and sat > accent_threshold:
        names = WARM_NAMES
    elif g > r * 1.04 and g >= b * 0.9 and sat > accent_threshold:
        names = GREEN_NAMES
    elif b >= r * 0.95 and b >= g * 0.9:
        names = BLUE_NAMES if background_bias != "light" else (BLUE_NAMES | LIGHT_NAMES)
    elif brightness > 145:
        names = LIGHT_NAMES if background_bias != "blue" else (LIGHT_NAMES | BLUE_NAMES)
    else:
        names = BLUE_NAMES | LIGHT_NAMES
    sub = {n: hx for n, hx in palette.items() if n in names}
    return sub or palette


def semantic_palette_color(rgb: np.ndarray, palette: Dict[str, str], *, global_nearest: bool = False,
                           background_bias: str = "balanced", accent_strength: float = 0.7) -> tuple[str, str, float]:
    return nearest_palette_color(rgb, palette if global_nearest else _palette_family_for_rgb(rgb, palette, background_bias, accent_strength))

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
                     diagonal_randomness: float, gradient_strength: float, pattern_mode: str = "Image Sampling", global_nearest: bool = False, background_bias: str = "balanced", accent_strength: float = 0.7) -> Panel:
    choices = []
    for split in ("TL_BR", "BL_TR"):
        a_pts, b_pts = triangle_points(panel.rect, split)
        a_rgb = _apply_gradient(_sample_polygon(image, a_pts), panel.rect, image.height, gradient_strength)
        b_rgb = _apply_gradient(_sample_polygon(image, b_pts), panel.rect, image.height, gradient_strength)
        a_name, a_hex, _ = semantic_palette_color(a_rgb, palette, global_nearest=global_nearest, background_bias=background_bias, accent_strength=accent_strength)
        b_name, b_hex, _ = semantic_palette_color(b_rgb, palette, global_nearest=global_nearest, background_bias=background_bias, accent_strength=accent_strength)
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



def build_manual_motif(size: tuple[int, int], motif_type: str, repeat_n: int, mirror: bool,
                       palette: Dict[str, str] | None = None) -> Image.Image:
    """Generate a coarse repeatable geometric motif image for façade sampling."""
    palette = palette or PALETTE
    w, h = size
    repeat_n = max(1, int(repeat_n))
    rows = 6
    cell_w = max(1, w // repeat_n)
    cell_h = max(1, h // rows)
    colors = {
        "bg": palette.get("POLAR WHITE", "#BFD8E8"),
        "blue": palette.get("DEEP BLUE", "#233A78"),
        "dark": palette.get("BLACK CLEAR", "#000000"),
        "green": palette.get("GREEN", "#438A62"),
        "warm": palette.get("TERRACOTTA", "#874836"),
        "light": palette.get("WHITE", "#EEF2FA"),
    }
    img = Image.new("RGB", size, colors["bg"])
    draw = ImageDraw.Draw(img)
    for x0 in range(0, w + cell_w, cell_w):
        phase = (x0 // cell_w) % repeat_n
        if mirror and phase >= repeat_n / 2:
            phase = repeat_n - 1 - phase
        cx = x0 + cell_w / 2
        for r in range(rows):
            y0 = r * cell_h
            cy = y0 + cell_h / 2
            if motif_type == "diamond":
                fill = colors["blue"] if (phase + r) % 2 else colors["warm"]
                draw.polygon([(cx, y0 + 4), (x0 + cell_w - 4, cy), (cx, y0 + cell_h - 4), (x0 + 4, cy)], fill=fill)
            elif motif_type == "chevron":
                fill = colors["blue"] if r % 2 else colors["dark"]
                draw.polygon([(x0, y0), (cx, cy), (x0, y0 + cell_h)], fill=fill)
                draw.polygon([(x0 + cell_w, y0), (cx, cy), (x0 + cell_w, y0 + cell_h)], fill=fill)
            elif motif_type == "dark-center diamond":
                draw.polygon([(cx, y0 + 2), (x0 + cell_w - 2, cy), (cx, y0 + cell_h - 2), (x0 + 2, cy)], fill=colors["warm"])
                m = min(cell_w, cell_h) * 0.25
                draw.polygon([(cx, cy - m), (cx + m, cy), (cx, cy + m), (cx - m, cy)], fill=colors["dark"])
            elif motif_type == "stepped textile band":
                step = max(2, cell_h // 4)
                fill = [colors["dark"], colors["blue"], colors["green"], colors["warm"]][(phase + r) % 4]
                draw.rectangle([x0, y0 + step, x0 + cell_w * 0.35, y0 + cell_h - step], fill=fill)
                draw.rectangle([x0 + cell_w * 0.35, y0 + 2 * step, x0 + cell_w * 0.7, y0 + cell_h], fill=fill)
                draw.rectangle([x0 + cell_w * 0.7, y0, x0 + cell_w, y0 + cell_h - 2 * step], fill=fill)
            elif motif_type == "sail motif":
                fill = colors["blue"] if r < rows / 2 else colors["dark"]
                draw.polygon([(x0 + cell_w * 0.15, y0 + cell_h), (x0 + cell_w * 0.85, y0 + cell_h), (cx, y0)], fill=fill)
                if (phase + r) % 3 == 0:
                    draw.polygon([(x0 + cell_w * 0.2, y0 + cell_h), (cx, cy), (x0 + cell_w * 0.8, y0 + cell_h)], fill=colors["light"])
    return img

def generate_pattern(layout: list[Panel], reference: Image.Image, columns: int, accent_limit: int = 3,
                     symmetry_mode: str = "none", repeat_n: int = 4, seed: int = 0,
                     diagonal_randomness: float = 0.0, gradient_strength: float = 0.0,
                     sail_motif: bool = False, top_trim: str = DEFAULT_TOP_TRIM,
                     bottom_trim: str = DEFAULT_BOTTOM_TRIM, palette: Dict[str, str] | None = None,
                     enabled_palette_colors: Iterable[str] | None = None,
                     window_glass_color: str | None = None, pattern_mode: str = "Image Sampling",
                     palette_groups: Iterable[str] | None = None, global_nearest: bool = False,
                     accent_strength: float = 0.7, background_bias: str = "balanced") -> list[Panel]:
    """Assign split directions and palette colors to all layout panels."""
    rng = np.random.default_rng(seed)
    facade_w = int(max(p.rect.x2 for p in layout))
    facade_h = int(max(p.rect.y2 for p in layout))
    image = reference.convert("RGB").resize((facade_w, facade_h), Image.Resampling.NEAREST if pattern_mode == "Graphic Motif" else Image.Resampling.LANCZOS)
    palette = palette or PALETTE
    pal = usable_palette(accent_limit, palette, enabled_palette_colors) if global_nearest else palette_from_groups(palette_groups, palette, enabled_palette_colors)

    full = [_pick_full_panel(image, p, pal, rng, diagonal_randomness, gradient_strength, pattern_mode, global_nearest, background_bias, accent_strength) for p in layout if p.panel_type == "full"]
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
