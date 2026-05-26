"""
Faceted Tile Map — choropleth-style US tile map faceted by date.

Available for Location × Numeric × Date (X = state column, Y = numeric measure,
Z = date column).  Each panel shows the tile map for one consolidated date period
(Year, Quarter, Month, or Week — configurable via Quick Edit).  Up to 12 panels
are shown; when the data has more periods, the most recent ones are kept.

All panels share a single colour scale and a single shared colorbar so that
values are directly comparable across panels.

Date grouping is by date component, collapsing across years:
  Year    → panel per distinct year         (keys: 2020, 2021 …)
  Quarter → panel per quarter number        (Q1 – Q4, merged across all years)
  Month   → panel per month number          (Jan – Dec, merged across all years)
  Week    → panel per ISO week number       (Wk 1 – Wk 52/53, merged across all years)
"""
from __future__ import annotations
import calendar
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
import matplotlib.colors as mcolors
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import PALETTE_CHOICES

# ── Reuse tile-grid definitions from the bivariate tile map ──────────────────
from charts.bivariate.tile_map import (
    _TILEMAP, _NROWS, _NCOLS, _to_abbrev,
)

MAX_PANELS = 12

# Labels for quarter / month — keyed by their integer code
_QUARTER_LABELS = {1: "Q1", 2: "Q2", 3: "Q3", 4: "Q4"}
_MONTH_LABELS   = {i: calendar.month_abbr[i] for i in range(1, 13)}


def _period_key_series(dates: pd.Series, date_unit: str) -> pd.Series:
    """Return an integer key series used to group rows into panels."""
    if date_unit == "Year":
        return dates.dt.year
    if date_unit == "Quarter":
        return dates.dt.quarter
    # Month
    return dates.dt.month


def _key_to_label(key: int, date_unit: str) -> str:
    """Human-readable panel title for a numeric period key."""
    if date_unit == "Year":
        return str(key)
    if date_unit == "Quarter":
        return _QUARTER_LABELS.get(key, f"Q{key}")
    # Month
    return _MONTH_LABELS.get(key, str(key))


class FacetedTileMap(BaseChart):
    CHART_ID       = "faceted_tile_map"
    DISPLAY_NAME   = "Faceted Tile Map"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",            "type": "text",   "default": ""},
            "palette":    {"label": "Colour palette",   "type": "choice", "default": "Blues",
                           "choices": PALETTE_CHOICES},
            "agg_func":   {"label": "Aggregation",      "type": "choice", "default": "Mean",
                           "choices": ["Mean", "Sum", "Count", "Median", "Min", "Max"]},
            "date_unit":  {"label": "Date grouping",    "type": "choice", "default": "Year",
                           "choices": ["Year", "Quarter", "Month"]},
            "ncols":      {"label": "Columns",          "type": "text",   "default": "3"},
            "show_label": {"label": "Show state labels","type": "bool",   "default": True},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()

        loc_col  = selection.x_var
        val_col  = selection.y_var
        date_col = selection.group_var

        if val_col is None or date_col is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5,
                    "Select a numeric Y-Axis and a date Z-Axis variable.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        # ── Prepare data ──────────────────────────────────────────────────────
        df_work = df[[loc_col, val_col, date_col]].copy()
        df_work[loc_col]  = df_work[loc_col].astype(str).map(_to_abbrev)
        df_work[val_col]  = pd.to_numeric(df_work[val_col], errors='coerce')
        df_work[date_col] = pd.to_datetime(df_work[date_col], errors='coerce')
        df_work = df_work.dropna()

        if df_work.empty:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5,
                    "No data matched US state names / abbreviations or date values.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11, wrap=True)
            return

        # ── Date grouping — by date component, collapsed across years ─────────
        date_unit = self._opt("date_unit") or "Year"
        df_work["_period_key"] = _period_key_series(df_work[date_col], date_unit)

        all_keys = sorted(df_work["_period_key"].unique())
        if len(all_keys) > MAX_PANELS:
            all_keys = all_keys[-MAX_PANELS:]  # keep highest keys (most recent)

        if not all_keys:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No date periods found in the data.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Aggregate per (state, period key) ─────────────────────────────────
        agg_name = (self._opt("agg_func") or "Mean").lower()
        agg_map  = {
            "mean": "mean", "sum": "sum", "count": "count",
            "median": "median", "min": "min", "max": "max",
        }
        agg_func = agg_map.get(agg_name, "mean")

        state_period = (
            df_work[df_work["_period_key"].isin(all_keys)]
            .groupby([loc_col, "_period_key"])[val_col]
            .agg(agg_func)
        )  # MultiIndex Series: (state_abbrev, period_key) → value

        # ── Global colour scale (shared across all panels) ────────────────────
        all_vals = state_period.values
        vmin = float(all_vals.min()) if len(all_vals) else 0.0
        vmax = float(all_vals.max()) if len(all_vals) else 1.0
        if vmin == vmax:
            vmax = vmin + 1.0

        palette = self._opt("palette") or "Blues"
        try:
            cmap = plt.cm.get_cmap(palette)
        except Exception:
            cmap = plt.cm.get_cmap("Blues")
        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

        # ── Layout ────────────────────────────────────────────────────────────
        n_panels = len(all_keys)
        try:
            ncols = max(1, min(int(self._opt("ncols") or 3), n_panels))
        except (TypeError, ValueError):
            ncols = 3
        nrows = int(np.ceil(n_panels / ncols))

        axes = fig.subplots(nrows, ncols, squeeze=False)
        show_lbl  = bool(self._opt("show_label"))
        tile_size = 0.9
        gap       = (1 - tile_size) / 2

        # ── Draw one tile map per panel ───────────────────────────────────────
        for idx, key in enumerate(all_keys):
            row, col_idx = divmod(idx, ncols)
            ax = axes[row][col_idx]

            # State values for this period key
            try:
                sv: pd.Series = state_period.xs(key, level="_period_key")
            except KeyError:
                sv = pd.Series(dtype=float)

            for abbrev, (tile_row, tile_col) in _TILEMAP.items():
                y = (_NROWS - 1 - tile_row)
                x = tile_col

                if abbrev in sv.index:
                    val       = sv[abbrev]
                    color     = cmap(norm(val))
                    edge      = "white"
                    lbl_color = "#0F172A" if mcolors.rgb_to_hsv(color[:3])[2] > 0.5 else "white"
                else:
                    color     = "#E2E8F0"
                    edge      = "white"
                    lbl_color = "#94A3B8"

                rect = mpatches.FancyBboxPatch(
                    (x + gap, y + gap), tile_size, tile_size,
                    boxstyle="round,pad=0.05",
                    facecolor=color, edgecolor=edge, linewidth=0.8,
                )
                ax.add_patch(rect)

                if show_lbl:
                    ax.text(x + 0.5, y + 0.5, abbrev,
                            ha='center', va='center',
                            fontsize=4, fontweight='bold', color=lbl_color)

            ax.set_xlim(-0.2, _NCOLS + 0.2)
            ax.set_ylim(-0.2, _NROWS + 0.2)
            ax.set_aspect('equal')
            ax.axis('off')
            ax.set_facecolor(self._chart_bg())
            ax.set_title(
                _key_to_label(key, date_unit),
                fontsize=9, fontweight='bold',
                color=self._text_color(), pad=4,
            )

        # Hide unused panels
        for idx in range(n_panels, nrows * ncols):
            row, col_idx = divmod(idx, ncols)
            axes[row][col_idx].set_visible(False)

        # ── Single shared colorbar — placed in reserved right margin ─────────
        # Reserve space on the right for the colorbar so it never overlaps panels.
        # subplots_adjust(right) leaves the panels in [0, right]; the colorbar
        # axis occupies the strip just outside that boundary.
        fig.subplots_adjust(right=0.80, top=0.88, hspace=0.4, wspace=0.25)
        cbar_ax = fig.add_axes([0.83, 0.12, 0.03, 0.70])

        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        y_label = VariableTransformer.axis_label(val_col, selection.y_transform())
        agg_lbl = (self._opt("agg_func") or "Mean").capitalize()
        cb = fig.colorbar(sm, cax=cbar_ax)
        cb.set_label(f"{agg_lbl} of {y_label}", fontsize=9,
                     color=self._text_color())
        cb.ax.tick_params(labelsize=8, colors=self._text_color())
        cb.outline.set_edgecolor(self._spine_color())

        # ── Title — sits in the top margin above the panels ──────────────────
        title = self._opt("title") or f"{y_label} by State — by {date_unit}"
        self._apply_suptitle(fig, title, fontsize=11, y=0.96)
        fig.patch.set_facecolor(self._chart_bg())
