"""Streamlit UI for the Facade Pattern Generator."""
from __future__ import annotations

from io import BytesIO

import streamlit as st
from PIL import Image

from exporters import draw_png, export_csv, export_png, export_svg, schedule_dataframe
from facade_layout import build_layout, canvas_size, parse_window_columns
from palette import DEFAULT_BOTTOM_TRIM, DEFAULT_TOP_TRIM, PALETTE
from pattern_engine import generate_pattern

st.set_page_config(page_title="Facade Pattern Generator", layout="wide")
st.title("Facade Pattern Generator")
st.caption("Deterministic triangular solar-glass façade elevations from a reference image.")

with st.sidebar:
    st.header("Reference")
    upload = st.file_uploader("Upload reference image", type=["png", "jpg", "jpeg", "webp"])

    st.header("Facade layout")
    columns = st.slider("Number of façade columns", 3, 30, 12)
    panel_row_height = st.slider("Panel row height", 160, 420, 260, 10)
    top_trim_height = st.slider("Top trim height", 0, 120, 34, 2)
    bottom_trim_height = st.slider("Bottom trim height", 0, 120, 34, 2)
    window_text = st.text_input("Window column positions (1-based, comma-separated)", "4,5,8,9")

    st.header("Color and pattern controls")
    accent_limit = st.slider("Accent color limit", 0, 5, 3)
    symmetry_mode = st.selectbox("Symmetry mode", ["none", "mirror around center", "repeat every N bays"])
    repeat_n = st.number_input("Repeat every N bays", min_value=1, max_value=12, value=4, disabled=symmetry_mode != "repeat every N bays")
    seed = st.number_input("Random seed", min_value=0, max_value=999999, value=42)
    diagonal_randomness = st.slider("Diagonal randomness strength", 0.0, 1.0, 0.0, 0.05)
    gradient_strength = st.slider("Dark-bottom / light-top gradient strength", 0.0, 1.0, 0.15, 0.05)
    sail_motif = st.checkbox("Enable sail motif mode", value=False)

    st.header("Trim colors")
    top_trim = st.selectbox("Top trim color", list(PALETTE.keys()), index=list(PALETTE.keys()).index(DEFAULT_TOP_TRIM))
    bottom_trim = st.selectbox("Bottom trim color", list(PALETTE.keys()), index=list(PALETTE.keys()).index(DEFAULT_BOTTOM_TRIM))

if upload is None:
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
)
layout = build_layout(
    columns=columns,
    window_columns=window_columns,
    width=size[0],
    panel_height=panel_row_height,
    top_trim_height=top_trim_height,
    bottom_trim_height=bottom_trim_height,
)
panels = generate_pattern(
    layout,
    reference,
    columns=columns,
    accent_limit=accent_limit,
    symmetry_mode=symmetry_mode,
    repeat_n=int(repeat_n),
    seed=int(seed),
    diagonal_randomness=diagonal_randomness,
    gradient_strength=gradient_strength,
    sail_motif=sail_motif,
    top_trim=top_trim,
    bottom_trim=bottom_trim,
)
preview = draw_png(panels, size)

left, right = st.columns([2, 1])
with left:
    st.subheader("Elevation preview")
    st.image(preview, use_container_width=True)
with right:
    st.subheader("Reference")
    st.image(reference, use_container_width=True)
    st.subheader("Exports")
    st.download_button("Download PNG", data=export_png(panels, size), file_name="facade_pattern.png", mime="image/png")
    st.download_button("Download SVG", data=export_svg(panels, size), file_name="facade_pattern.svg", mime="image/svg+xml")
    st.download_button("Download CSV panel schedule", data=export_csv(panels), file_name="facade_panel_schedule.csv", mime="text/csv")

st.subheader("Panel schedule")
st.dataframe(schedule_dataframe(panels), use_container_width=True)

with st.expander("Palette"):
    st.json(PALETTE)
