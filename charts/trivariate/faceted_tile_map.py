"""
Faceted Tile Map — choropleth-style US tile map faceted by date.

Available for Location × Numeric × Date (X = state column, Y = numeric measure,
Z = date column).  Each panel shows the tile map for one consolidated date period
(Year, Quarter, Month, or Week — configurable via Quick Edit).  Up to 12 panels
are shown; when the data has more periods, the most recent ones are kept.

All panels share a single colour scale and a single shared colorbar so that
values are directly comparable across panels.
"""
from __future__ import annotations
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
                           "choices": ["Year", "Quarter", "Month", "Week"]},
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

        # ── Date grouping ─────────────────────────────────────────────────────
        date_unit = self._opt("date_unit") or "Year"
        freq_map  = {"Year": "Y", "Quarter": "Q", "Month": "M", "Week": "W"}
        freq      = freq_map.get(date_unit, "Y")

        df_work["_period"] = df_work[date_col].dt.to_period(freq)
        all_periods = sorted(df_work["_period"].unique())
        if len(all_periods) > MAX_PANELS:
            all_periods = all_periods[-MAX_PANELS:]  # keep most recent

        if not all_periods:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No date periods found in the data.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Aggregate per (state, period) ─────────────────────────────────────
        agg_name = (self._opt("agg_func") or "Mean").lower()
        agg_map  = {
            "mean": "mean", "sum": "sum", "count": "count",
            "median": "median", "min": "min", "max": "max",
        }
        agg_func = agg_map.get(agg_name, "mean")

        state_period = (
            df_work[df_work["_period"].isin(all_periods)]
            .groupby([loc_col, "_period"])[val_col]
            .agg(agg_func)
        )  # MultiIndex Series: (state_abbrev, period) → value

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
        n_panels = len(all_periods)
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
        for idx, period in enumerate(all_periods):
            row, col_idx = divmod(idx, ncols)
            ax = axes[row][col_idx]

            # State values for this period
            try:
                sv: pd.Series = state_period.xs(period, level="_period")
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
                self._fmt_period(period, freq),
                fontsize=9, fontweight='bold',
                color=self._text_color(), pad=4,
            )

        # Hide unused panels
        for idx in range(n_panels, nrows * ncols):
            row, col_idx = divmod(idx, ncols)
            axes[row][col_idx].set_visible(False)

        # ── Single shared colorbar ────────────────────────────────────────────
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        y_label  = VariableTransformer.axis_label(val_col, selection.y_transform())
        agg_lbl  = (self._opt("agg_func") or "Mean").capitalize()
        ax_list  = [axes[r][c] for r in range(nrows) for c in range(ncols)]
        cb = fig.colorbar(sm, ax=ax_list, shrink=0.6, pad=0.02, aspect=25)
        cb.set_label(f"{agg_lbl} of {y_label}", fontsize=9)
        cb.ax.tick_params(labelsize=8)

        # ── Title ─────────────────────────────────────────────────────────────
        title = self._opt("title") or f"{y_label} by State — by {date_unit}"
        self._apply_suptitle(fig, title, fontsize=11)
        fig.patch.set_facecolor(self._chart_bg())

    # ── Helper ────────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_period(period, freq: str) -> str:
        """Return a human-readable label for a pandas Period."""
        if freq == "Y":
            return str(period.year)
        if freq == "Q":
            return f"{period.year} Q{period.quarter}"
        if freq == "M":
            return period.start_time.strftime("%b %Y")
        # Week
        return period.start_time.strftime("Wk %b %-d, %Y")
