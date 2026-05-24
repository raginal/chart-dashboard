"""
Faceted Histogram / Faceted Column Chart — distribution of X shown separately
for each Y-Axis category.

Lives in the **bivariate** tab.  X + Y are required; Y must be categorical.

• Numeric X      → histogram (binned bar chart of frequencies)  — "Faceted Histogram"
• Categorical X  → bar chart of value counts                    — "Faceted Column Chart"

Each panel corresponds to one value of the Y-Axis variable.
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT, MPL_DEFAULT_PALETTE, PALETTE_CHOICES

MAX_FACETS = 16


class FacetedHistogram(BaseChart):
    CHART_ID       = "faceted_histogram"
    DISPLAY_NAME   = "Faceted Histogram"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",                      "type": "text",   "default": ""},
            "color":      {"label": "Bar colour (Histogram)",     "type": "text",   "default": MPL_ACCENT},
            "palette":    {"label": "Bar palette (Column Chart)", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                           "choices": PALETTE_CHOICES},
            "ncols":      {"label": "Columns",                    "type": "text",   "default": "3"},
            "num_bins":   {"label": "Bins (numeric X)",           "type": "text",   "default": "10"},
            "sort_order": {"label": "Facet order",                "type": "choice", "default": "Ascending",
                           "choices": ["Ascending", "Descending", "As-is"]},
            "shared_x":   {"label": "Shared X range",             "type": "bool",   "default": True},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()

        x_col   = selection.x_var
        fac_col = selection.y_var   # facet by Y-Axis (must be categorical)

        if fac_col is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "Select a Y-Axis variable to facet by.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        cols_needed = [c for c in [x_col, fac_col] if c is not None]
        sub = df[cols_needed].dropna()

        if sub.empty:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data after removing missing values.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # Sort facets
        sort_order = self._opt("sort_order") or "Ascending"
        raw_facets = sub[fac_col].unique().tolist()
        if sort_order == "Ascending":
            try:
                facets = sorted(raw_facets)
            except TypeError:
                facets = sorted(raw_facets, key=str)
        elif sort_order == "Descending":
            try:
                facets = sorted(raw_facets, reverse=True)
            except TypeError:
                facets = sorted(raw_facets, key=str, reverse=True)
        else:
            facets = raw_facets

        if len(facets) > MAX_FACETS:
            facets = facets[:MAX_FACETS]

        try:
            ncols = max(1, min(int(self._opt("ncols") or 3), len(facets)))
        except (TypeError, ValueError):
            ncols = 3

        nrows = int(np.ceil(len(facets) / ncols))

        # Detect X type and prepare data
        x_type     = selection.x_type()
        is_numeric = x_type in (VariableType.INTERVAL, VariableType.DATE)
        x_numeric  = pd.to_numeric(sub[x_col], errors='coerce') if is_numeric else None

        # ── Colours ───────────────────────────────────────────────────────────
        # Histogram: single accent colour, same across all panels
        # Column chart: palette mapped to X categories, same mapping across all panels
        hist_color = self._opt("color") or MPL_ACCENT
        palette    = self._opt("palette") or MPL_DEFAULT_PALETTE

        # For categorical: consistent label ordering + per-category colour map
        if not is_numeric:
            all_cats = sorted(sub[x_col].astype(str).unique(), key=str)
            try:
                cmap     = plt.cm.get_cmap(palette, max(len(all_cats), 2))
                x_colors = [cmap(i / max(len(all_cats) - 1, 1))
                             for i in range(len(all_cats))]
            except Exception:
                x_colors = [MPL_ACCENT] * len(all_cats)

        # Compute shared bin edges for numeric X
        try:
            n_bins = max(2, min(int(self._opt("num_bins") or 10), 30))
        except (TypeError, ValueError):
            n_bins = 10

        shared_x  = bool(self._opt("shared_x"))
        bin_edges = None
        if is_numeric and x_numeric is not None and not x_numeric.dropna().empty:
            x_min = float(x_numeric.min())
            x_max = float(x_numeric.max())
            if x_min < x_max:
                bin_edges = np.linspace(x_min, x_max, n_bins + 1)

        axes = fig.subplots(nrows, ncols, squeeze=False)

        for idx, facet in enumerate(facets):
            row, col = divmod(idx, ncols)
            ax = axes[row][col]
            mask   = sub[fac_col] == facet
            x_vals = sub.loc[mask, x_col]

            if is_numeric:
                x_num = pd.to_numeric(x_vals, errors='coerce').dropna()
                if x_num.empty:
                    ax.text(0.5, 0.5, "No data", ha='center', va='center',
                            transform=ax.transAxes, color="#94A3B8", fontsize=8)
                else:
                    if bin_edges is not None and shared_x:
                        ax.hist(x_num, bins=bin_edges, color=hist_color, alpha=0.85,
                                edgecolor="white", linewidth=0.5, zorder=2)
                    else:
                        ax.hist(x_num, bins=n_bins, color=hist_color, alpha=0.85,
                                edgecolor="white", linewidth=0.5, zorder=2)
            else:
                counts = x_vals.astype(str).value_counts()
                counts = counts.reindex(all_cats, fill_value=0)
                # Bars coloured by X category — same mapping across every panel
                ax.bar(range(len(all_cats)), counts.values, color=x_colors, alpha=0.85,
                       zorder=2)
                ax.set_xticks(range(len(all_cats)))
                n_cats = len(all_cats)
                ax.set_xticklabels(
                    all_cats,
                    rotation=45 if n_cats > 5 else 0,
                    ha='right' if n_cats > 5 else 'center',
                    fontsize=max(6, 8 - max(n_cats - 5, 0)),
                )

            ax.set_title(str(facet), fontsize=9, fontweight='bold', pad=4)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(labelsize=8)
            ax.set_ylabel("Count", fontsize=7)

        # Hide unused panels
        for idx in range(len(facets), nrows * ncols):
            row, col = divmod(idx, ncols)
            axes[row][col].set_visible(False)

        x_label = VariableTransformer.axis_label(x_col, selection.x_transform())
        y_col   = selection.y_var
        title   = self._opt("title") or f"Distribution of {x_label} by {y_col}"

        fig.tight_layout(rect=[0.0, 0.04, 1.0, 0.93])
        self._apply_suptitle(fig, title)
        fig.supxlabel(x_label, fontsize=10, y=0.01)
        fig.patch.set_facecolor("white")
