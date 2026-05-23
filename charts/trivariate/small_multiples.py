"""
Small Multiples — faceted grid of scatter or line sub-charts.

Lives in the **trivariate** tab (requires X + Y + Z-Axis).

The Z-Axis variable is the facet variable.  Each panel shows X vs Y for one
value of Z.  Facet sort order is configurable via Edit…
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


class SmallMultiples(BaseChart):
    CHART_ID       = "small_multiples"
    DISPLAY_NAME   = "Small Multiples"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":       {"label": "Title",                    "type": "text",   "default": ""},
            "chart_type":  {"label": "Sub-chart type",           "type": "choice", "default": "Scatter",
                            "choices": ["Scatter", "Line"]},
            "palette":     {"label": "Colour palette",           "type": "choice", "default": MPL_DEFAULT_PALETTE,
                            "choices": PALETTE_CHOICES},
            "same_color":  {"label": "Same colour across panels","type": "bool",   "default": True},
            "shared_axes": {"label": "Shared axis ranges",       "type": "bool",   "default": True},
            "ncols":       {"label": "Columns",                  "type": "text",   "default": "3"},
            "sort_order":  {"label": "Facet order",              "type": "choice", "default": "Ascending",
                            "choices": ["Ascending", "Descending", "As-is"]},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()

        x_col   = selection.x_var
        y_col   = selection.y_var
        fac_col = selection.group_var

        if fac_col is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "Select a Z-Axis variable to facet by.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        sub = df[[x_col, y_col, fac_col]].dropna()

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
        chart_type = self._opt("chart_type") or "Scatter"

        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        same_color = self._opt("same_color")
        same_color = True if same_color is None else bool(same_color)
        try:
            cmap = plt.cm.get_cmap(palette, max(len(facets), 2))
            if same_color:
                # All panels share the first palette colour
                colors = [cmap(0.0)] * len(facets)
            else:
                colors = [cmap(i / max(len(facets) - 1, 1)) for i in range(len(facets))]
        except Exception:
            colors = [MPL_ACCENT] * len(facets)

        shared_axes = self._opt("shared_axes")
        shared_axes = True if shared_axes is None else bool(shared_axes)
        axes = fig.subplots(nrows, ncols, squeeze=False,
                            sharex=shared_axes, sharey=shared_axes)

        x_type = selection.x_type()
        y_type = selection.y_type()

        for idx, (facet, color) in enumerate(zip(facets, colors)):
            row, col = divmod(idx, ncols)
            ax = axes[row][col]
            mask = sub[fac_col] == facet
            xs   = self._to_mpl_numeric(sub.loc[mask, x_col], x_type)
            ys   = self._to_mpl_numeric(sub.loc[mask, y_col], y_type)

            if chart_type == "Scatter":
                valid = xs.notna() & ys.notna()
                ax.scatter(xs[valid], ys[valid], color=color, alpha=0.6, s=14, linewidths=0)

            elif chart_type == "Line":
                valid = xs.notna() & ys.notna()
                order = xs[valid].argsort()
                ax.plot(xs[valid].iloc[order], ys[valid].iloc[order],
                        color=color, linewidth=1.5)

            ax.set_title(str(facet), fontsize=9, fontweight='bold', pad=4)
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.tick_params(labelsize=8)

        # Apply date formatters to shared axes (setting on any one panel propagates)
        if len(facets) > 0:
            ref_ax = axes[0][0]
            if x_type == VariableType.DATE:
                self._apply_date_fmt(ref_ax, 'x', fig)
            if y_type == VariableType.DATE:
                self._apply_date_fmt(ref_ax, 'y')

        # Hide unused panels
        for idx in range(len(facets), nrows * ncols):
            row, col = divmod(idx, ncols)
            axes[row][col].set_visible(False)

        x_label = VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = VariableTransformer.axis_label(y_col, selection.y_transform())
        title   = self._opt("title") or f"{y_col} vs {x_col} — faceted by {fac_col}"

        fig.tight_layout(rect=[0.03, 0.04, 1.0, 0.93])
        fig.suptitle(title, fontsize=12, fontweight='bold', y=0.98)
        fig.supxlabel(x_label, fontsize=10, y=0.01)
        fig.supylabel(y_label, fontsize=10, x=0.0)
        fig.patch.set_facecolor("white")
