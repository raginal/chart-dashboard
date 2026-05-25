"""
US State Tile Map — choropleth-style grid map of the United States.

Available for Location × Numeric pairs (X = state column, Y = numeric measure).
Each state is rendered as a coloured square positioned on a fixed tile grid
that approximates geographic layout.  Missing states are drawn as light grey
outlines.  A colourbar legend shows the value scale.

Aggregation: if multiple rows share the same state, values are averaged by
default (configurable via Quick Edit).
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
from core.variable_classifier import US_STATE_ABBREVS, US_STATE_NAMES
from core.transformer import VariableTransformer
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES

# ── Tile grid positions (row, col) — 0-indexed, row 0 = top ──────────────────
# Layout approximates geographic positions using an 8 × 11 grid.
_TILEMAP: dict[str, tuple[int, int]] = {
    'ME': (0, 10),
    'WI': (1,  5), 'VT': (1, 9), 'NH': (1, 10),
    'WA': (2,  0), 'ID': (2, 1), 'MT': (2, 2), 'ND': (2, 3), 'MN': (2, 4),
    'IL': (2,  5), 'MI': (2, 6), 'NY': (2, 8), 'MA': (2, 9),
    'OR': (3,  0), 'NV': (3, 1), 'WY': (3, 2), 'SD': (3, 3), 'IA': (3, 4),
    'IN': (3,  5), 'OH': (3, 6), 'PA': (3, 7), 'NJ': (3, 8), 'CT': (3, 9),
    'RI': (3, 10),
    'CA': (4,  0), 'UT': (4, 1), 'CO': (4, 2), 'NE': (4, 3), 'MO': (4, 4),
    'KY': (4,  5), 'WV': (4, 6), 'VA': (4, 7), 'MD': (4, 8), 'DE': (4, 9),
    'AZ': (5,  1), 'NM': (5, 2), 'KS': (5, 3), 'AR': (5, 4), 'TN': (5, 5),
    'NC': (5,  6), 'SC': (5, 7), 'DC': (5, 8),
    'OK': (6,  3), 'LA': (6, 4), 'MS': (6, 5), 'AL': (6, 6), 'GA': (6, 7),
    'HI': (7,  0), 'AK': (7, 1), 'TX': (7, 3), 'FL': (7, 7),
}

_NROWS = 8
_NCOLS = 11

# Full state name → abbreviation
_NAME_TO_ABBREV: dict[str, str] = {
    'alabama': 'AL', 'alaska': 'AK', 'arizona': 'AZ', 'arkansas': 'AR',
    'california': 'CA', 'colorado': 'CO', 'connecticut': 'CT',
    'delaware': 'DE', 'florida': 'FL', 'georgia': 'GA', 'hawaii': 'HI',
    'idaho': 'ID', 'illinois': 'IL', 'indiana': 'IN', 'iowa': 'IA',
    'kansas': 'KS', 'kentucky': 'KY', 'louisiana': 'LA', 'maine': 'ME',
    'maryland': 'MD', 'massachusetts': 'MA', 'michigan': 'MI',
    'minnesota': 'MN', 'mississippi': 'MS', 'missouri': 'MO',
    'montana': 'MT', 'nebraska': 'NE', 'nevada': 'NV',
    'new hampshire': 'NH', 'new jersey': 'NJ', 'new mexico': 'NM',
    'new york': 'NY', 'north carolina': 'NC', 'north dakota': 'ND',
    'ohio': 'OH', 'oklahoma': 'OK', 'oregon': 'OR', 'pennsylvania': 'PA',
    'rhode island': 'RI', 'south carolina': 'SC', 'south dakota': 'SD',
    'tennessee': 'TN', 'texas': 'TX', 'utah': 'UT', 'vermont': 'VT',
    'virginia': 'VA', 'washington': 'WA', 'west virginia': 'WV',
    'wisconsin': 'WI', 'wyoming': 'WY', 'district of columbia': 'DC',
}


def _fmt_tile_value(v: float) -> str:
    """Compact number formatter for tile labels (e.g. 1.2M, 34.5K, 3.1)."""
    av = abs(v)
    if av >= 1_000_000:
        return f"{v / 1_000_000:.1f}M"
    if av >= 1_000:
        return f"{v / 1_000:.1f}K"
    if av >= 100:
        return f"{v:.0f}"
    return f"{v:.1f}"


def _to_abbrev(value: str) -> str | None:
    """Normalise a state name or abbreviation to a two-letter abbreviation."""
    v = str(value).strip()
    upper = v.upper()
    if upper in US_STATE_ABBREVS:
        return upper
    lower = v.lower()
    return _NAME_TO_ABBREV.get(lower)


class TileMap(BaseChart):
    CHART_ID       = "tile_map"
    DISPLAY_NAME   = "US Tile Map"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",           "type": "text",   "default": ""},
            "palette":    {"label": "Colour palette",   "type": "choice", "default": "Blues",
                           "choices": PALETTE_CHOICES},
            "agg_func":   {"label": "Aggregation",      "type": "choice", "default": "Mean",
                           "choices": ["Mean", "Sum", "Count", "Median", "Min", "Max"]},
            "show_label": {"label": "Show state labels", "type": "bool",   "default": True},
            "show_value": {"label": "Show values",       "type": "bool",   "default": False},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        loc_col = selection.x_var
        val_col = selection.y_var

        if val_col is None:
            ax.text(0.5, 0.5, "Select a numeric Y-Axis variable to colour the map.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        df_work = df[[loc_col, val_col]].copy()
        df_work[loc_col] = df_work[loc_col].astype(str).map(_to_abbrev)
        df_work[val_col] = pd.to_numeric(df_work[val_col], errors='coerce')
        df_work = df_work.dropna()

        if df_work.empty:
            ax.text(0.5, 0.5, "No data matched US state names or abbreviations.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Aggregate per state ────────────────────────────────────────────────
        agg_name = (self._opt("agg_func") or "Mean").lower()
        agg_map  = {
            "mean": "mean", "sum": "sum", "count": "count",
            "median": "median", "min": "min", "max": "max",
        }
        agg_func = agg_map.get(agg_name, "mean")
        state_vals: pd.Series = getattr(
            df_work.groupby(loc_col)[val_col], agg_func
        )()

        vmin = float(state_vals.min())
        vmax = float(state_vals.max())
        if vmin == vmax:
            vmax = vmin + 1.0   # avoid degenerate colormap

        palette = self._opt("palette") or "Blues"
        try:
            cmap = plt.cm.get_cmap(palette)
        except Exception:
            cmap = plt.cm.get_cmap("Blues")

        norm = mcolors.Normalize(vmin=vmin, vmax=vmax)

        # ── Draw tiles ────────────────────────────────────────────────────────
        tile_size  = 0.9        # fraction of cell (leaves a small gap)
        gap        = (1 - tile_size) / 2
        show_lbl   = bool(self._opt("show_label"))
        show_val   = bool(self._opt("show_value"))
        both       = show_lbl and show_val

        for abbrev, (row, col) in _TILEMAP.items():
            # Invert row so row 0 is at the top
            y = (_NROWS - 1 - row)
            x = col

            if abbrev in state_vals.index:
                val       = state_vals[abbrev]
                color     = cmap(norm(val))
                edge      = "white"
                lbl_color = "#0F172A" if mcolors.rgb_to_hsv(color[:3])[2] > 0.5 else "white"
            else:
                val       = None
                color     = "#E2E8F0"   # light grey for missing states
                edge      = "white"
                lbl_color = "#94A3B8"

            rect = mpatches.FancyBboxPatch(
                (x + gap, y + gap), tile_size, tile_size,
                boxstyle="round,pad=0.05",
                facecolor=color, edgecolor=edge, linewidth=1.2,
            )
            ax.add_patch(rect)

            if show_lbl:
                # When both labels are shown, shift abbreviation up to make room
                lbl_y = (y + 0.63) if both else (y + 0.5)
                ax.text(x + 0.5, lbl_y, abbrev,
                        ha='center', va='center',
                        fontsize=6 if both else 7,
                        fontweight='bold', color=lbl_color)

            if show_val and val is not None:
                val_str = _fmt_tile_value(val)
                val_y   = (y + 0.33) if both else (y + 0.5)
                ax.text(x + 0.5, val_y, val_str,
                        ha='center', va='center',
                        fontsize=5.5, color=lbl_color)

        # ── Axes housekeeping ─────────────────────────────────────────────────
        ax.set_xlim(-0.2, _NCOLS + 0.2)
        ax.set_ylim(-0.2, _NROWS + 0.2)
        ax.set_aspect('equal')
        ax.axis('off')

        # ── Colorbar ──────────────────────────────────────────────────────────
        sm = plt.cm.ScalarMappable(cmap=cmap, norm=norm)
        sm.set_array([])
        cb = fig.colorbar(sm, ax=ax, shrink=0.55, pad=0.02, aspect=20)
        y_label = VariableTransformer.axis_label(val_col, selection.y_transform())
        agg_label = (self._opt("agg_func") or "Mean").capitalize()
        cb.set_label(f"{agg_label} of {y_label}", fontsize=9)
        cb.ax.tick_params(labelsize=8)

        # ── Title ─────────────────────────────────────────────────────────────
        title = self._opt("title") or f"{y_label} by State ({agg_label})"
        self._apply_title(ax, title, pad=12)

        fig.patch.set_facecolor(self._chart_bg())
        fig.tight_layout()
