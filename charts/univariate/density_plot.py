from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from scipy.stats import gaussian_kde

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class DensityPlot(BaseChart):
    CHART_ID       = "density_plot"
    DISPLAY_NAME   = "Density Plot"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text", "default": ""},
            "x_label": {"label": "X-axis label", "type": "text", "default": ""},
            "color":   {"label": "Curve colour", "type": "text", "default": MPL_ACCENT},
            "fill":    {"label": "Fill under curve", "type": "bool", "default": True},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        vtype  = selection.x_type()
        df_work, sampled = self._large_data_sample(df, 50_000)
        series = self._to_mpl_numeric(df_work[col], vtype).dropna().values

        if len(series) < 3:
            ax.text(0.5, 0.5, "Not enough data for a density plot (need ≥ 3 values).",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        try:
            kde = gaussian_kde(series)
        except Exception:
            ax.text(0.5, 0.5, "Could not compute kernel density estimate.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        xs    = np.linspace(series.min(), series.max(), 500)
        ys    = kde(xs)
        color = self._opt("color") or MPL_ACCENT

        ax.plot(xs, ys, color=color, linewidth=2)
        if self._opt("fill"):
            ax.fill_between(xs, ys, alpha=0.2, color=color)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel("Density")
        ax.set_ylim(bottom=0)
        ax.set_title(self._opt("title") or f"Density Plot — {col}", fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        if sampled:
            self._add_sample_note(ax, 50_000)
        fig.tight_layout()
