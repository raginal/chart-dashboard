"""
Column Chart — univariate bar chart of category counts.

Only shown for Nominal / Ordinal variables.
Bars are sorted by count (default) or alphabetically by value.
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


class ColumnChart(BaseChart):
    CHART_ID       = "column_chart"
    DISPLAY_NAME   = "Column Chart"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":    {"label": "Title",           "type": "text",   "default": ""},
            "palette":  {"label": "Colour palette",   "type": "choice", "default": MPL_DEFAULT_PALETTE,
                         "choices": PALETTE_CHOICES},
            "sort_by":  {"label": "Sort bars by",     "type": "choice", "default": "Count",
                         "choices": ["Count", "Value"]},
            "rotate_x": {"label": "Rotate X labels",  "type": "bool",   "default": False},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col      = selection.x_var
        var_type = selection.x_type()

        # Guard: only meaningful for categorical variables
        if var_type in (VariableType.INTERVAL, VariableType.DATE):
            ax.text(
                0.5, 0.5,
                "Column Chart is for categorical variables.\n"
                "Use Histogram or Density Plot for numeric data.",
                ha="center", va="center", transform=ax.transAxes,
                color="#94A3B8", fontsize=11, wrap=True,
            )
            return

        series = df[col].dropna().astype(str)

        if series.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        counts  = series.value_counts()
        sort_by = self._opt("sort_by") or "Count"
        if sort_by == "Value":
            counts = counts.sort_index()
        # else: already sorted by count descending

        labels = counts.index.tolist()
        values = counts.values.tolist()
        n      = len(labels)

        # ── Colours ───────────────────────────────────────────────────────────
        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        try:
            cmap   = plt.cm.get_cmap(palette, max(n, 2))
            colors = [cmap(i / max(n - 1, 1)) for i in range(n)]
        except Exception:
            colors = [MPL_ACCENT] * n

        # ── Draw bars ─────────────────────────────────────────────────────────
        x_pos = np.arange(n)
        ax.bar(x_pos, values, color=colors, width=0.65, zorder=2)
        ax.set_xticks(x_pos)

        rotate = bool(self._opt("rotate_x")) or n > 10
        ax.set_xticklabels(
            labels,
            rotation=45 if rotate else 0,
            ha="right" if rotate else "center",
            fontsize=max(6, 9 - max(n - 10, 0) // 4),
        )

        x_label = VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel("Count")
        ax.set_title(
            self._opt("title") or f"Distribution — {x_label}",
            fontsize=13, fontweight="bold", pad=10,
        )

        self._apply_figure_style(fig, ax)
        fig.tight_layout()
