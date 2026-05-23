"""Empirical Cumulative Distribution Function (ECDF) plot."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.ticker as ticker
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class CumulativeDensity(BaseChart):
    CHART_ID       = "cumulative_density"
    DISPLAY_NAME   = "Cumulative Density"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text", "default": ""},
            "x_label": {"label": "X-axis label", "type": "text", "default": ""},
            "color":   {"label": "Line colour",  "type": "text", "default": MPL_ACCENT},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        vtype  = selection.x_type()
        series = self._to_mpl_numeric(df[col], vtype).dropna().values

        if len(series) == 0:
            ax.text(0.5, 0.5, "No numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        xs    = np.sort(series)
        ys    = np.arange(1, len(xs) + 1) / len(xs)
        color = self._opt("color") or MPL_ACCENT

        ax.step(xs, ys, color=color, linewidth=2, where='post')
        ax.fill_between(xs, ys, step='post', alpha=0.12, color=color)

        ax.set_ylim(0, 1.05)
        ax.yaxis.set_major_formatter(ticker.PercentFormatter(xmax=1))

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel("Cumulative proportion")
        ax.set_title(self._opt("title") or f"Cumulative Density — {col}",
                     fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
