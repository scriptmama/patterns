# Facade Pattern Generator

A standalone Python + Streamlit app for deterministic architectural façade elevation studies. The app samples a user-uploaded reference image and reduces it to a controlled system of rectangular solar-glass panels, where every full rectangular panel is split into exactly two triangles and colored from an editable palette.

This is **not** an AI image-generation tool. It is a rule-based pattern engine for clean elevation previews, SVG/PNG output, and CSV panel schedules.

## What the app does

- Upload a reference image and map it onto a 3-row façade grid.
- Configure the number of vertical bays/columns.
- Place rectangular window openings in the middle row by column number.
- Test both allowed diagonal splits for every full panel:
  - `TL_BR`: top-left to bottom-right
  - `BL_TR`: bottom-left to top-right
- Sample each triangular region from the reference image.
- Quantize sampled colors to the nearest color in a fixed editable palette.
- Choose the diagonal direction that best approximates the image region.
- Keep windows as light neutral glass.
- Keep dummy panels beside windows as narrow rectangles that inherit nearby full-panel colors.
- Add configurable top and bottom trim rectangles, including independent trim heights.
- Export PNG, SVG, and CSV panel schedules.

## Installation

```bash
pip install -r requirements.txt
```

## Run the app

```bash
streamlit run app.py
```

Open the local Streamlit URL shown in your terminal.

## Using a reference image

1. Start the app.
2. Use **Upload reference image** in the sidebar.
3. Choose a PNG, JPG, JPEG, or WEBP file.
4. The app resizes the reference internally to the façade canvas and samples the image over panel triangle regions.

## Configuring the façade

### Columns

Use **Number of façade columns** to control the vertical bay count.

### Window positions

Use **Window column positions** to enter 1-based column numbers for windows in the middle row. Separate multiple columns with commas.

Example:

```text
4,5,8,9
```

This places windows in columns 4, 5, 8, and 9 of the middle row. Window openings remain rectangular and are not triangulated.

### Palette and pattern controls

- **Accent color limit** limits how many accent colors are available beyond the core blue/neutral palette.
- **Symmetry mode** can be:
  - `none`
  - `mirror around center`
  - `repeat every N bays`
- **Random seed** makes randomized tie-breaking and motif bias deterministic.
- **Diagonal randomness strength** adds controlled variation to diagonal choice while keeping output repeatable for the same seed.
- **Dark-bottom / light-top gradient strength** biases lower panels darker and upper panels lighter.
- **Sail motif mode** optionally encourages grouped dark blue, navy, or charcoal triangles to form vertical sail-like shapes across stacked rectangles.

### Trim colors

Top and bottom trim colors are configurable from the palette. Defaults are:

- Top trim: `ice_blue` (`#D9EAF2`)
- Bottom trim: `ral_5010` (`#004F9E`)

## Exports

The app provides download buttons for:

- **PNG**: raster elevation preview.
- **SVG**: vector elevation with triangle and rectangle geometry.
- **CSV panel schedule**: one row per full panel, window, or dummy panel.

CSV columns:

```text
panel_id,row,col,panel_type,split_direction,triangle_a_color_name,triangle_a_hex,triangle_b_color_name,triangle_b_hex
```

Window example:

```csv
W_04,1,4,window,NONE,window_glass,#EAF5F8,window_glass,#EAF5F8
```

Dummy panel example:

```csv
D_04_L,1,4,dummy,NONE,ral_5010,#004F9E,ral_5010,#004F9E
```

## Geometric constraints

The generator intentionally enforces strict architectural pattern rules:

- Each full rectangular panel is exactly two triangles.
- Full panels have no extra subdivisions.
- No trapezoids, irregular quadrilaterals, or extra facets are generated.
- Window openings are rectangular.
- Dummy panels beside windows are narrow rectangles and inherit adjacent full-panel color.
- Top and bottom trims are horizontal rectangles and are not triangulated.

## Palette

The default editable palette is defined in `palette.py`:

```python
PALETTE = {
    "ice_blue": "#D9EAF2",
    "light_blue": "#AFC9DD",
    "medium_blue": "#5F8DB4",
    "ral_5010": "#004F9E",
    "dark_navy": "#102D46",
    "charcoal": "#1C252A",
    "coral_red": "#C94B43",
    "soft_pink": "#E7A6A2",
    "muted_green": "#6D8A78",
    "muted_yellow": "#E5C45A",
    "window_glass": "#EAF5F8",
    "door_ral_5015": "#007BC7",
}
```

## Known limitations

- The first version prioritizes a reliable MVP over perfect visual reconstruction.
- Sampling uses average color per triangle, so small details in the reference image are simplified.
- The sail motif is a deterministic bias layer, not a structural optimization algorithm.
- Dummy panels inherit a nearby full-panel color and are not independently image-sampled.
- The layout is fixed to 3 panel rows plus top and bottom trim; row and trim heights can be adjusted while façade width remains controlled by the column count and preview width.
- The app does not integrate with Rhino, Grasshopper, BIM, or CAD systems.
