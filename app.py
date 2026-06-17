"""Streamlit UI for the Facade Pattern Generator."""
from __future__ import annotations

import json

import streamlit as st
from PIL import Image

from exporters import draw_png, export_csv, export_png, export_svg, schedule_dataframe
from facade_layout import build_layout, canvas_size, parse_window_columns
from palette import DEFAULT_BOTTOM_TRIM, DEFAULT_TOP_TRIM, PALETTE, PALETTE_GROUPS, DEFAULT_PALETTE_GROUPS, SPECIAL_COLORS, WINDOW_COLOR
from pattern_engine import build_manual_motif, generate_pattern, prepare_reference_image

APP_VERSION = "2.0"


def get_default_settings() -> dict:
    return {
        "version": APP_VERSION,
        "columns": 12,
        "row_mode": "3",
        "row_heights": [260, 260, 260],
        "panel_row_height": 260,
        "odd_panel_width": 100,
        "even_panel_width": 100,
        "top_trim_height": 34,
        "bottom_trim_height": 34,
        "window_columns": [4, 5, 8, 9],
        "window_text": "4,5,8,9",
        "palette": dict(PALETTE),
        "enabled_palette_colors": list(PALETTE),
        "allowed_palette_groups": list(DEFAULT_PALETTE_GROUPS),
        "pattern_preset": "Greenlandic textile",
        "pattern_mode": "Graphic Motif",
        "manual_motif_type": "diamond",
        "manual_mirror_center": True,
        "accent_color_limit": 3,
        "symmetry_mode": "mirror around center",
        "repeat_every_n_bays": 4,
        "random_seed": 42,
        "diagonal_randomness_strength": 0.0,
        "gradient_strength": 0.0,
        "sail_motif_mode": False,
        "reference_crop_mode": "full image",
        "manual_crop_left": 0,
        "manual_crop_top": 0,
        "manual_crop_right": 100,
        "manual_crop_bottom": 100,
        "reference_x_offset": 0,
        "reference_y_offset": 0,
        "reference_scale": 1.0,
        "tile_reference_horizontally": True,
        "mirror_tile": True,
        "active_motif_crop": True,
        "contrast_boost": 1.7,
        "saturation_boost": 1.6,
        "posterize_color_count": 6,
        "accent_strength": 0.8,
        "minimum_accent_cluster_size": 1,
        "background_blue_light_bias": "balanced",
        "advanced_global_nearest_color": False,
        "top_trim_color": DEFAULT_TOP_TRIM,
        "bottom_trim_color": DEFAULT_BOTTOM_TRIM,
        "door_color": SPECIAL_COLORS["door_color"],
        "window_glass_color": SPECIAL_COLORS[WINDOW_COLOR],
    }


def validate_settings(settings_dict: dict) -> dict:
    if not isinstance(settings_dict, dict):
        raise ValueError("settings JSON must contain an object")
    defaults = get_default_settings()
    loaded = {**defaults, **{k: v for k, v in settings_dict.items() if k in defaults}}
    loaded["row_mode"] = "6" if str(loaded.get("row_mode")) == "6" else "3"
    loaded["palette"] = {**PALETTE, **(loaded.get("palette") or {})}
    loaded["enabled_palette_colors"] = [c for c in loaded.get("enabled_palette_colors", list(PALETTE)) if c in loaded["palette"]]
    if not loaded["enabled_palette_colors"]:
        loaded["enabled_palette_colors"] = list(PALETTE)
    loaded["allowed_palette_groups"] = [g for g in loaded.get("allowed_palette_groups", list(DEFAULT_PALETTE_GROUPS)) if g in PALETTE_GROUPS]
    if not loaded["allowed_palette_groups"]:
        loaded["allowed_palette_groups"] = list(DEFAULT_PALETTE_GROUPS)
    loaded["columns"] = int(max(3, min(30, loaded["columns"])))
    loaded["panel_row_height"] = int(max(50, min(420, loaded["panel_row_height"])))
    loaded["odd_panel_width"] = int(max(50, min(200, loaded["odd_panel_width"])))
    loaded["even_panel_width"] = int(max(50, min(200, loaded["even_panel_width"])))
    loaded["top_trim_height"] = int(max(0, min(120, loaded["top_trim_height"])))
    loaded["bottom_trim_height"] = int(max(0, min(120, loaded["bottom_trim_height"])))
    loaded["window_columns"] = [int(c) for c in loaded.get("window_columns", []) if 1 <= int(c) <= loaded["columns"]]
    loaded["window_text"] = loaded.get("window_text") or ",".join(str(c) for c in loaded["window_columns"])
    return loaded


def apply_loaded_settings(settings_dict: dict) -> None:
    settings = validate_settings(settings_dict)
    for key, value in settings.items():
        st.session_state[key] = value
    st.session_state["settings_loaded"] = True


def serialize_settings(settings: dict) -> dict:
    row_count = 6 if settings["row_mode"] == "6" else 3
    try:
        window_columns = [c + 1 for c in parse_window_columns(settings["window_text"], settings["columns"])]
    except ValueError:
        window_columns = []
    return {
        **settings,
        "version": APP_VERSION,
        "row_heights": [settings["panel_row_height"]] * row_count,
        "window_columns": window_columns,
    }


st.set_page_config(page_title="Facade Pattern Generator", layout="wide")
st.title("Facade Pattern Generator")
st.caption("Deterministic triangular solar-glass façade elevations from a reference image.")

for key, value in get_default_settings().items():
    st.session_state.setdefault(key, value)

with st.sidebar:
    st.header("Reference")
    upload = st.file_uploader("Upload reference image", type=["png", "jpg", "jpeg", "webp"])
    settings_upload = st.file_uploader("Load settings JSON", type=["json"])
    if settings_upload is not None:
        try:
            apply_loaded_settings(json.load(settings_upload))
        except (json.JSONDecodeError, TypeError, ValueError) as exc:
            st.error(f"Could not load settings JSON: {exc}")
    if st.session_state.pop("settings_loaded", False):
        st.success("Settings loaded. Upload the same reference image to reproduce the pattern exactly.")

    preset = st.selectbox("Pattern style preset", ["Feininger sails", "Greenlandic textile", "Blue gradient", "Manufacturer neutral", "Advanced custom"], key="pattern_preset")
    if preset != "Advanced custom":
        preset_mode = {"Feininger sails": "Manual Motif", "Greenlandic textile": "Graphic Motif", "Blue gradient": "Image Sampling", "Manufacturer neutral": "Image Sampling"}[preset]
        st.session_state.pattern_mode = preset_mode
        if preset == "Feininger sails":
            st.session_state.manual_motif_type = "sail motif"
            st.session_state.symmetry_mode = "mirror around center"
        elif preset == "Greenlandic textile":
            st.session_state.contrast_boost = 1.7
            st.session_state.saturation_boost = 1.6
            st.session_state.posterize_color_count = 6
        elif preset == "Blue gradient":
            st.session_state.gradient_strength = 0.55
            st.session_state.allowed_palette_groups = ["blue_field", "light_field", "dark_accents"]
        elif preset == "Manufacturer neutral":
            st.session_state.allowed_palette_groups = ["light_field", "blue_field", "dark_accents"]
            st.session_state.gradient_strength = 0.1

    pattern_mode = st.radio("Pattern pipeline mode", ["Image Sampling", "Graphic Motif", "Manual Motif"], key="pattern_mode", help="Image Sampling keeps the original photo-sampling behavior. Graphic Motif simplifies textiles/beadwork first. Manual Motif creates a repeatable geometric source.")

    with st.expander("Facade layout", expanded=True):
        columns = st.slider("Number of façade columns", 3, 30, key="columns")
        row_mode = st.radio("Panel row mode", ["3", "6"], format_func=lambda value: f"{value} rows", horizontal=True, key="row_mode")
        panel_row_height = st.slider("Panel row height", 50, 420, step=10, key="panel_row_height")
        odd_panel_width = st.slider("Odd column panel width", 50, 200, step=5, key="odd_panel_width")
        even_panel_width = st.slider("Even column panel width", 50, 200, step=5, key="even_panel_width")
        top_trim_height = st.slider("Top trim height", 0, 120, step=2, key="top_trim_height")
        bottom_trim_height = st.slider("Bottom trim height", 0, 120, step=2, key="bottom_trim_height")
        window_text = st.text_input("Window column positions (1-based, comma-separated)", key="window_text")

    with st.expander("Reference mapping", expanded=False):
        crop_mode = st.selectbox("Reference crop mode", ["full image", "center crop", "manual crop"], key="reference_crop_mode")
        if crop_mode == "manual crop":
            st.slider("Manual crop left %", 0, 95, key="manual_crop_left")
            st.slider("Manual crop top %", 0, 95, key="manual_crop_top")
            st.slider("Manual crop right %", 5, 100, key="manual_crop_right")
            st.slider("Manual crop bottom %", 5, 100, key="manual_crop_bottom")
        st.slider("X offset", -100, 100, key="reference_x_offset")
        st.slider("Y offset", -100, 100, key="reference_y_offset")
        st.slider("Scale", 0.25, 3.0, step=0.05, key="reference_scale")
        st.checkbox("Tile reference horizontally", key="tile_reference_horizontally")
        st.checkbox("Mirror tile", key="mirror_tile")
        st.checkbox("Auto-crop to active motif area", key="active_motif_crop", disabled=pattern_mode != "Graphic Motif")

    with st.expander("Graphic and motif controls", expanded=pattern_mode != "Image Sampling"):
        if pattern_mode == "Manual Motif":
            st.selectbox("Motif type", ["diamond", "chevron", "dark-center diamond", "stepped textile band", "sail motif"], key="manual_motif_type")
            st.checkbox("Mirror motif around center", key="manual_mirror_center")
        st.slider("Contrast boost", 0.5, 3.0, step=0.05, key="contrast_boost")
        st.slider("Saturation boost", 0.0, 3.0, step=0.05, key="saturation_boost")
        st.slider("Posterize color count", 2, 16, key="posterize_color_count")
        st.slider("Accent strength", 0.0, 1.0, step=0.05, key="accent_strength")
        st.slider("Minimum accent cluster size", 1, 6, key="minimum_accent_cluster_size")
        st.selectbox("Background blue/light bias", ["balanced", "blue", "light"], key="background_blue_light_bias")
        st.selectbox("Symmetry mode", ["none", "mirror around center", "repeat every N bays"], key="symmetry_mode")
        st.number_input("Repeat every N bays", min_value=1, max_value=12, key="repeat_every_n_bays")

    with st.expander("Palette", expanded=False):
        allowed_palette_groups = st.multiselect("Allowed palette groups", list(PALETTE_GROUPS), key="allowed_palette_groups")
        enabled_palette_colors = st.multiselect("Enabled manufacturer colors", list(PALETTE), key="enabled_palette_colors")
        st.checkbox("Advanced: global nearest color", key="advanced_global_nearest_color")
        accent_limit = st.slider("Legacy accent color limit", 0, 5, key="accent_color_limit")

    with st.expander("Advanced technical controls", expanded=False):
        seed = st.number_input("Random seed", min_value=0, max_value=999999, key="random_seed")
        diagonal_randomness = st.slider("Diagonal randomness strength", 0.0, 1.0, step=0.05, key="diagonal_randomness_strength")
        gradient_strength = st.slider("Dark-bottom / light-top gradient strength", 0.0, 1.0, step=0.05, key="gradient_strength")
        sail_motif = st.checkbox("Legacy sail motif overlay", key="sail_motif_mode")

    with st.expander("Special non-façade colors", expanded=False):
        trim_options = list(SPECIAL_COLORS) + list(PALETTE)
        for custom_trim in (st.session_state.get("top_trim_color"), st.session_state.get("bottom_trim_color")):
            if custom_trim and custom_trim not in trim_options:
                trim_options.append(custom_trim)
        top_trim = st.selectbox("Top trim color", trim_options, key="top_trim_color")
        bottom_trim = st.selectbox("Bottom trim color", trim_options, key="bottom_trim_color")
        window_glass_color = st.color_picker("Window glass color", key="window_glass_color")
        door_color = st.color_picker("Door color", key="door_color")

current_settings = serialize_settings({key: st.session_state[key] for key in get_default_settings()})

if upload is None:
    st.download_button(
        "Download settings JSON",
        data=json.dumps(current_settings, indent=2).encode("utf-8"),
        file_name="facade_pattern_settings.json",
        mime="application/json",
    )
    st.info("Upload a reference image to generate a façade elevation.")
    st.stop()

try:
    window_columns = parse_window_columns(window_text, columns)
except ValueError as exc:
    st.error(str(exc))
    st.stop()

reference = Image.open(upload)
size = canvas_size(
    panel_height=panel_row_height,
    top_trim_height=top_trim_height,
    bottom_trim_height=bottom_trim_height,
    columns=columns,
    odd_panel_width=odd_panel_width,
    even_panel_width=even_panel_width,
    row_mode=row_mode,
)
layout = build_layout(
    columns=columns,
    window_columns=window_columns,
    width=size[0],
    panel_height=panel_row_height,
    top_trim_height=top_trim_height,
    bottom_trim_height=bottom_trim_height,
    odd_panel_width=odd_panel_width,
    even_panel_width=even_panel_width,
    row_mode=row_mode,
)
manual_crop = (
    st.session_state.manual_crop_left / 100,
    st.session_state.manual_crop_top / 100,
    st.session_state.manual_crop_right / 100,
    st.session_state.manual_crop_bottom / 100,
)
if pattern_mode == "Manual Motif":
    reduced_reference = build_manual_motif(size, st.session_state.manual_motif_type, int(st.session_state.repeat_every_n_bays), st.session_state.manual_mirror_center, PALETTE)
else:
    reduced_reference = prepare_reference_image(
        reference,
        size,
        mode=pattern_mode,
        crop_mode=st.session_state.reference_crop_mode,
        manual_crop=manual_crop,
        x_offset=st.session_state.reference_x_offset,
        y_offset=st.session_state.reference_y_offset,
        scale=st.session_state.reference_scale,
        tile_horizontal=st.session_state.tile_reference_horizontally,
        mirror_tile=st.session_state.mirror_tile,
        contrast_boost=st.session_state.contrast_boost,
        saturation_boost=st.session_state.saturation_boost,
        posterize_colors=st.session_state.posterize_color_count,
        motif_grid_cols=columns,
        motif_grid_rows=6 if row_mode == "6" else 3,
        active_crop=st.session_state.active_motif_crop and pattern_mode == "Graphic Motif",
    )

panels = generate_pattern(
    layout,
    reduced_reference,
    columns=columns,
    accent_limit=accent_limit,
    symmetry_mode=symmetry_mode,
    repeat_n=int(st.session_state.repeat_every_n_bays),
    seed=int(seed),
    diagonal_randomness=diagonal_randomness,
    gradient_strength=gradient_strength,
    sail_motif=sail_motif,
    top_trim=top_trim,
    bottom_trim=bottom_trim,
    palette=PALETTE,
    enabled_palette_colors=enabled_palette_colors,
    window_glass_color=window_glass_color,
    pattern_mode=pattern_mode,
    palette_groups=allowed_palette_groups,
    global_nearest=st.session_state.advanced_global_nearest_color,
    accent_strength=st.session_state.accent_strength,
    background_bias=st.session_state.background_blue_light_bias,
)
preview = draw_png(panels, size)

left, middle, right = st.columns([2, 1, 1])
with left:
    st.subheader("Elevation preview")
    st.image(preview, use_container_width=True)
with middle:
    st.subheader("Reduced motif preview")
    st.image(reduced_reference, use_container_width=True)
with right:
    st.subheader("Reference")
    st.image(reference, use_container_width=True)
    st.subheader("Exports")
    st.download_button("Download PNG", data=export_png(panels, size), file_name="facade_pattern.png", mime="image/png")
    st.download_button("Download SVG", data=export_svg(panels, size), file_name="facade_pattern.svg", mime="image/svg+xml")
    st.download_button("Download CSV panel schedule", data=export_csv(panels, row_mode=row_mode), file_name="facade_panel_schedule.csv", mime="text/csv")
    st.download_button("Download settings JSON", data=json.dumps(current_settings, indent=2).encode("utf-8"), file_name="facade_pattern_settings.json", mime="application/json")

st.subheader("Panel schedule")
st.dataframe(schedule_dataframe(panels, row_mode=row_mode), use_container_width=True)

with st.expander("Palette"):
    st.json(PALETTE)
