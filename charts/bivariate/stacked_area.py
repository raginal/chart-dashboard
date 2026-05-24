"""Stacked area chart for time-series or continuous X vs numeric Y."""
from __future__ import annotations
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class StackedArea(BaseChart):
    CHART_ID       = "stacked_area"
    DISPLAY_NAME   = "Stacked Area Chart"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",        "type": "text", "default": ""},
            "x_label": {"label": "X-axis label",  "type": "text", "default": ""},
            "y_label": {"label": "Y-axis label",  "type": "text", "default": ""},
            "color":   {"label": "Fill colour",   "type": "text", "default": MPL_ACCENT},
            "alpha":   {"label": "Fill opacity",  "type": "text", "default": "0.6"},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col  = selection.x_var
        y_col  = selection.y_var
        x_type = selection.x_type()

        sub = df[[x_col, y_col]].copy()
        sub[x_col] = self._to_mpl_numeric(sub[x_col], x_type)
        sub[y_col] = pd.to_numeric(sub[y_col], errors='coerce')
        sub = sub.dropna().sort_values(x_col)

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        try:
            alpha = float(self._opt("alpha"))
        except (TypeError, ValueError):
            alpha = 0.6

        color = self._opt("color") or MPL_ACCENT
        ax.fill_between(sub[x_col], sub[y_col], alpha=alpha, color=color, zorder=2)
        ax.plot(sub[x_col], sub[y_col], color=color, linewidth=1.5, zorder=3)

        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_ylim(bottom=0)
        ax.set_title(self._opt("title") or f"{y_col} over {x_col}",
                     fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
