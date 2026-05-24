"""Line plot with optional confidence band (95% CI via bootstrapping or SEM)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT, MPL_CONFIDENCE_BAND


class LinePlot(BaseChart):
    CHART_ID       = "line_plot"
    DISPLAY_NAME   = "Line Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":     {"label": "Title",            "type": "text", "default": ""},
            "x_label":   {"label": "X-axis label",      "type": "text", "default": ""},
            "y_label":   {"label": "Y-axis label",      "type": "text", "default": ""},
            "color":     {"label": "Line colour",        "type": "text", "default": MPL_ACCENT},
            "conf_band": {"label": "Confidence band",    "type": "bool", "default": False},
            "markers":   {"label": "Show data markers",  "type": "bool", "default": False},
            "sort_x":    {"label": "Sort by X",          "type": "bool", "default": True},
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
        sub = sub.dropna()

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        if self._opt("sort_x"):
            sub = sub.sort_values(x_col)

        color  = self._opt("color") or MPL_ACCENT
        marker = 'o' if self._opt("markers") else None

        if self._opt("conf_band"):
            grouped = sub.groupby(x_col)[y_col]
            means   = grouped.mean()
            sems    = grouped.sem().fillna(0)
            xs = means.index
            ax.plot(xs, means.values, color=color, linewidth=2, marker=marker, markersize=5)
            ax.fill_between(
                xs,
                means.values - 1.96 * sems.values,
                means.values + 1.96 * sems.values,
                color=MPL_CONFIDENCE_BAND, alpha=0.5, label="95% CI",
            )
            ax.legend(fontsize=9, framealpha=0.8)
        else:
            ax.plot(sub[x_col], sub[y_col], color=color, linewidth=2,
                    marker=marker, markersize=5, alpha=0.85)

        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(self._opt("title") or f"{y_col} over {x_col}",
                     fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
