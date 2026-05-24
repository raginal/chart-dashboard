"""Quantile-Quantile plot against a normal distribution."""
from __future__ import annotations
import pandas as pd
import numpy as np
from matplotlib.figure import Figure
from scipy import stats

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT, MPL_TREND


class QQPlot(BaseChart):
    CHART_ID       = "qq_plot"
    DISPLAY_NAME   = "Q-Q Plot"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":       {"label": "Title",        "type": "text", "default": ""},
            "point_color": {"label": "Point colour",  "type": "text", "default": MPL_ACCENT},
            "line_color":  {"label": "Reference line","type": "text", "default": MPL_TREND},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        vtype  = selection.x_type()
        df_work, sampled = self._large_data_sample(df, 50_000)
        series = self._to_mpl_numeric(df_work[col], vtype).dropna().values

        if len(series) < 4:
            ax.text(0.5, 0.5, "Not enough data for a Q-Q plot (need ≥ 4 values).",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        point_color = self._opt("point_color") or MPL_ACCENT
        line_color  = self._opt("line_color")  or MPL_TREND

        # scipy.stats.probplot: returns (quantiles, values) and the fit line
        (theoretical_q, sample_q), (slope, intercept, r) = stats.probplot(series, dist="norm")

        ax.scatter(theoretical_q, sample_q, s=12, alpha=0.55,
                   color=point_color, linewidths=0, zorder=3)

        # Reference line (45-degree)
        line_x = np.array([theoretical_q.min(), theoretical_q.max()])
        ax.plot(line_x, slope * line_x + intercept, color=line_color,
                linewidth=1.5, zorder=2, label=f"R² = {r**2:.3f}")
        ax.legend(fontsize=9, framealpha=0.7)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'y')
        x_label = VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel("Theoretical quantiles (Normal)")
        ax.set_ylabel(f"Sample quantiles — {x_label}")
        self._apply_title(ax, self._opt("title") or f"Q-Q Plot — {col}")
        self._apply_figure_style(fig, ax)
        if sampled:
            self._add_sample_note(ax, 50_000)
        fig.tight_layout()
