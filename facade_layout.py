"""Facade layout primitives and deterministic geometry generation."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Literal

PanelType = Literal["full", "window", "dummy", "top_trim", "bottom_trim", "trim"]
SplitDirection = Literal["TL_BR", "BL_TR", "NONE"]


@dataclass(frozen=True)
class Rect:
    x: float
    y: float
    width: float
    height: float

    @property
    def x2(self) -> float:
        return self.x + self.width

    @property
    def y2(self) -> float:
        return self.y + self.height


@dataclass
class Panel:
    panel_id: str
    row: int
    col: int
    panel_type: PanelType
    rect: Rect
    split_direction: SplitDirection = "NONE"
    triangle_a_color_name: str = ""
    triangle_a_hex: str = ""
    triangle_b_color_name: str = ""
    triangle_b_hex: str = ""
    # Optional dummy side marker: L/R for narrow panels beside windows.
    side: str = ""


def parse_window_columns(text: str, columns: int) -> List[int]:
    """Parse comma-separated 1-based window columns into sorted 0-based indices."""
    if not text.strip():
        return []
    result = set()
    for raw in text.split(","):
        raw = raw.strip()
        if not raw:
            continue
        value = int(raw)
        if value < 1 or value > columns:
            raise ValueError(f"Window column {value} is outside 1..{columns}.")
        result.add(value - 1)
    return sorted(result)


def build_layout(
    columns: int,
    window_columns: Iterable[int],
    width: int = 1200,
    panel_height: int = 220,
    top_trim_height: int = 34,
    bottom_trim_height: int = 34,
    dummy_fraction: float = 0.16,
    row_mode: str = "3",
    trim_height: int | None = None,
    odd_panel_width: int | None = None,
    even_panel_width: int | None = None,
) -> list[Panel]:
    """Build a 3- or 6-row facade with optional windows and dummy side panels.

    In 3-row mode, windows occupy row 1. In 6-row mode, windows span rows 2
    and 3, while side dummy panels are split into upper/lower rectangles.
    """
    if trim_height is not None:
        top_trim_height = trim_height
        bottom_trim_height = trim_height
    if columns < 1:
        raise ValueError("columns must be at least 1")
    if panel_height < 1:
        raise ValueError("panel_height must be at least 1")
    if top_trim_height < 0 or bottom_trim_height < 0:
        raise ValueError("trim heights must be non-negative")
    if (odd_panel_width is None) != (even_panel_width is None):
        raise ValueError("odd_panel_width and even_panel_width must be provided together")
    if odd_panel_width is not None and even_panel_width is not None:
        if odd_panel_width < 1 or even_panel_width < 1:
            raise ValueError("panel widths must be at least 1")
        bay_widths = [odd_panel_width if col % 2 == 0 else even_panel_width for col in range(columns)]
        width = sum(bay_widths)
    else:
        bay_widths = [width / columns] * columns
    window_set = set(window_columns)
    panels: list[Panel] = []

    row_count = 6 if str(row_mode) == "6" else 3
    window_start = 2 if row_count == 6 else 1
    window_span = 2 if row_count == 6 else 1

    panels.append(Panel("T_TOP", -1, -1, "top_trim", Rect(0, 0, width, top_trim_height)))
    for row in range(row_count):
        y = top_trim_height + row * panel_height
        x = 0.0
        for col, bay_w in enumerate(bay_widths):
            if row_count == 3 and row == window_start and col in window_set:
                dummy_w = bay_w * dummy_fraction
                window_w = bay_w - 2 * dummy_w
                panels.append(Panel(f"D_{col + 1:02d}_L", row, col, "dummy", Rect(x, y, dummy_w, panel_height), side="L"))
                panels.append(Panel(f"W_{col + 1:02d}", row, col, "window", Rect(x + dummy_w, y, window_w, panel_height)))
                panels.append(Panel(f"D_{col + 1:02d}_R", row, col, "dummy", Rect(x + dummy_w + window_w, y, dummy_w, panel_height), side="R"))
            elif row_count == 6 and row == window_start and col in window_set:
                dummy_w = bay_w * dummy_fraction
                window_w = bay_w - 2 * dummy_w
                panels.append(Panel(f"D_{col + 1:02d}_L_upper", row, col, "dummy", Rect(x, y, dummy_w, panel_height), side="L"))
                panels.append(Panel(f"W_{col + 1:02d}", row, col, "window", Rect(x + dummy_w, y, window_w, panel_height * window_span)))
                panels.append(Panel(f"D_{col + 1:02d}_R_upper", row, col, "dummy", Rect(x + dummy_w + window_w, y, dummy_w, panel_height), side="R"))
            elif row_count == 6 and row == window_start + 1 and col in window_set:
                dummy_w = bay_w * dummy_fraction
                window_w = bay_w - 2 * dummy_w
                panels.append(Panel(f"D_{col + 1:02d}_L_lower", row, col, "dummy", Rect(x, y, dummy_w, panel_height), side="L"))
                panels.append(Panel(f"D_{col + 1:02d}_R_lower", row, col, "dummy", Rect(x + dummy_w + window_w, y, dummy_w, panel_height), side="R"))
            else:
                panels.append(Panel(f"P_{row}_{col + 1:02d}", row, col, "full", Rect(x, y, bay_w, panel_height)))
            x += bay_w
    panels.append(Panel("T_BOTTOM", row_count, -1, "bottom_trim", Rect(0, top_trim_height + row_count * panel_height, width, bottom_trim_height)))
    return panels


def canvas_size(
    width: int = 1200,
    panel_height: int = 220,
    top_trim_height: int = 34,
    bottom_trim_height: int = 34,
    trim_height: int | None = None,
    columns: int | None = None,
    odd_panel_width: int | None = None,
    even_panel_width: int | None = None,
    row_mode: str = "3",
) -> tuple[int, int]:
    if trim_height is not None:
        top_trim_height = trim_height
        bottom_trim_height = trim_height
    if (odd_panel_width is None) != (even_panel_width is None):
        raise ValueError("odd_panel_width and even_panel_width must be provided together")
    if odd_panel_width is not None and even_panel_width is not None:
        if columns is None:
            raise ValueError("columns must be provided when custom panel widths are used")
        if odd_panel_width < 1 or even_panel_width < 1:
            raise ValueError("panel widths must be at least 1")
        odd_columns = (columns + 1) // 2
        even_columns = columns // 2
        width = odd_columns * odd_panel_width + even_columns * even_panel_width
    row_count = 6 if str(row_mode) == "6" else 3
    return width, top_trim_height + bottom_trim_height + panel_height * row_count


def triangle_points(rect: Rect, split: SplitDirection) -> tuple[list[tuple[float, float]], list[tuple[float, float]]]:
    """Return exactly two triangle polygons for a rectangle and split direction."""
    if split == "TL_BR":
        return ([(rect.x, rect.y), (rect.x2, rect.y), (rect.x2, rect.y2)],
                [(rect.x, rect.y), (rect.x2, rect.y2), (rect.x, rect.y2)])
    if split == "BL_TR":
        return ([(rect.x, rect.y), (rect.x2, rect.y), (rect.x, rect.y2)],
                [(rect.x2, rect.y), (rect.x2, rect.y2), (rect.x, rect.y2)])
    raise ValueError("split must be TL_BR or BL_TR for full panels")
