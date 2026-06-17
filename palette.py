"""Color palettes for the Facade Pattern Generator."""

MANUFACTURER_PALETTE = {
    "BLACK CLEAR": "#000000",
    "ANTHRACITE": "#202A2F",
    "BLACK ACID": "#2B2D2D",
    "GREY": "#30333B",
    "POLAR GREY": "#9DB2BD",
    "POLAR WHITE": "#BFD8E8",
    "LIME WHITE": "#C6DAD2",
    "WHITE": "#EEF2FA",
    "BLUE": "#3156D4",
    "DEEP BLUE": "#233A78",
    "GREEN": "#438A62",
    "INTENSE GREEN": "#438A65",
    "CORAL BROWN": "#927459",
    "CLAY": "#9A4F37",
    "CORTEN STEEL": "#633731",
    "OCHER": "#8B572D",
    "SAND": "#B07C4D",
    "TERRACOTTA": "#874836",
    "MARBLE BROWN": "#4D4A40",
}

PALETTE_GROUPS = {
    "light_field": ["POLAR WHITE", "WHITE", "LIME WHITE", "POLAR GREY", "SAND"],
    "blue_field": ["BLUE", "DEEP BLUE", "POLAR GREY", "POLAR WHITE"],
    "dark_accents": ["BLACK CLEAR", "ANTHRACITE", "BLACK ACID", "GREY", "MARBLE BROWN", "DEEP BLUE"],
    "green_accents": ["GREEN", "INTENSE GREEN", "LIME WHITE"],
    "warm_accents": ["CORAL BROWN", "CLAY", "CORTEN STEEL", "OCHER", "SAND", "TERRACOTTA", "MARBLE BROWN"],
}

DEFAULT_PALETTE_GROUPS = ["light_field", "blue_field", "dark_accents", "green_accents", "warm_accents"]

# Backwards-compatible default palette name used throughout the app.
PALETTE = MANUFACTURER_PALETTE

# Non-facade colors remain independent from the manufacturer panel palette.
SPECIAL_COLORS = {
    "window_glass": "#EAF5F8",
    "door_color": "#007BC7",
    "top_trim_color": "#BFD8E8",
    "bottom_trim_color": "#3156D4",
}

DEFAULT_TOP_TRIM = "top_trim_color"
DEFAULT_BOTTOM_TRIM = "bottom_trim_color"
WINDOW_COLOR = "window_glass"
DOOR_COLOR = "door_color"
