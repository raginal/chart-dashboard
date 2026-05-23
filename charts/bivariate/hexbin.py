"""Hexbin density plot for two numeric variables."""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import PALETTE_CHOICES


class Hexbin(BaseChart):
    CHART_ID       = "hexbin"
    DISPLAY_NAME   = "Hexbin Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",        "type": "text",   "default": ""},
            "x_label": {"label": "X-axis label",  "type": "text",   "default": ""},
            "y_label": {"label": "Y-axis label",  "type": "text",   "default": ""},
            "palette": {"label": "Colour map",    "type": "choice", "default": "Blues",
                        "choices": PALETTE_CHOICES},
            "gridsize":{"label": "Grid size",     "type": "text",   "default": "30"},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col, y_col = selection.x_var, selection.y_var
        x_type = selection.x_type()
        y_type = selection.y_type()
        sub = df[[x_col, y_col]].copy()
        sub[x_col] = self._to_mpl_numeric(sub[x_col], x_type)
        sub[y_col] = self._to_mpl_numeric(sub[y_col], y_type)
        sub = sub.dropna()

        if len(sub) < 10:
            ax.text(0.5, 0.5, "Not enough data for a hexbin plot (need ≥ 10 rows).",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        try:
            gridsize = int(float(self._opt("gridsize") or 30))
        except (TypeError, ValueError):
            gridsize = 30
        gridsize = max(5, min(gridsize, 100))

        palette = self._opt("palette") or "Blues"
        hb = ax.hexbin(sub[x_col], sub[y_col], gridsize=gridsize,
                       cmap=palette, mincnt=1, linewidths=0.3, edgecolors='white')
        plt.colorbar(hb, ax=ax, label="Count", shrink=0.8)

        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        if y_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'y')

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        ax.set_title(self._opt("title") or f"{y_col} vs {x_col} (Hexbin)", fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
