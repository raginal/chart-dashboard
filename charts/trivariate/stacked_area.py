"""
Stacked Area Chart — X (numeric/date) × Y (numeric) × Z (categorical/location).

The Z-Axis variable defines the colour bands: one stacked area layer per Z
value.  Y is aggregated (mean or sum) per (X, Z) pair before plotting.

Lives in the **trivariate** tab (requires X + Y + Z-Axis).
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

MAX_CATEGORIES = 20


class StackedArea(BaseChart):
    CHART_ID       = "stacked_area"
    DISPLAY_NAME   = "Stacked Area Chart"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":    {"label": "Title",          "type": "text",   "default": ""},
            "x_label":  {"label": "X-axis label",   "type": "text",   "default": ""},
            "y_label":  {"label": "Y-axis label",   "type": "text",   "default": ""},
            "agg_func": {"label": "Aggregate Y by", "type": "choice", "default": "Sum",
                         "choices": ["Sum", "Mean"]},
            "palette":  {"label": "Colour palette", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                         "choices": PALETTE_CHOICES},
            "alpha":    {"label": "Fill opacity",   "type": "text",   "default": "0.75"},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col  = selection.x_var
        y_col  = selection.y_var
        z_col  = selection.group_var
        x_type = selection.x_type()

        if z_col is None:
            ax.text(0.5, 0.5, "Select a Z-Axis variable to define the stacked areas.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        sub = df[[x_col, y_col, z_col]].copy()
        sub[x_col] = self._to_mpl_numeric(sub[x_col], x_type)
        sub[y_col] = pd.to_numeric(sub[y_col], errors='coerce')
        sub = sub.dropna()

        if sub.empty:
            ax.text(0.5, 0.5, "No data after removing missing values.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Aggregate Y per (X, Z) ────────────────────────────────────────────
        agg_func = self._opt("agg_func") or "Sum"
        func = "sum" if agg_func == "Sum" else "mean"

        pivot = (sub.groupby([x_col, z_col])[y_col]
                    .agg(func)
                    .unstack(fill_value=0)
                    .sort_index())

        # Cap categories to prevent an illegible chart
        categories = pivot.columns.tolist()
        if len(categories) > MAX_CATEGORIES:
            pivot      = pivot[categories[:MAX_CATEGORIES]]
            categories = categories[:MAX_CATEGORIES]
            ax.annotate(f"Showing first {MAX_CATEGORIES} of {len(pivot.columns)} categories",
                        xy=(0.01, 0.99), xycoords='axes fraction',
                        fontsize=7, color="#94A3B8", va='top')

        # ── Colours ───────────────────────────────────────────────────────────
        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        try:
            cmap   = plt.cm.get_cmap(palette, max(len(categories), 2))
            colors = [cmap(i / max(len(categories) - 1, 1))
                      for i in range(len(categories))]
        except Exception:
            colors = [MPL_ACCENT] * len(categories)

        try:
            alpha = float(self._opt("alpha"))
        except (TypeError, ValueError):
            alpha = 0.75

        # ── Draw ──────────────────────────────────────────────────────────────
        ax.stackplot(pivot.index, pivot.T.values,
                     labels=categories, colors=colors, alpha=alpha)

        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)

        ax.set_ylim(bottom=0)
        ax.legend(loc='upper left', fontsize=8, framealpha=0.7,
                  title=z_col, title_fontsize=8)

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(f"{agg_func} of {y_label}")
        ax.set_title(self._opt("title") or f"{agg_func} of {y_col} over {x_col} by {z_col}",
                     fontsize=13, fontweight='bold', pad=10)

        self._apply_figure_style(fig, ax)
        fig.tight_layout()
