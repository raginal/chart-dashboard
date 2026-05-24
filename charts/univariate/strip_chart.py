"""Strip chart — jittered dot plot for visualising the full distribution."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class StripChart(BaseChart):
    CHART_ID       = "strip_chart"
    DISPLAY_NAME   = "Strip Chart"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text", "default": ""},
            "x_label": {"label": "X-axis label", "type": "text", "default": ""},
            "color":   {"label": "Point colour", "type": "text", "default": MPL_ACCENT},
            "alpha":   {"label": "Opacity (0–1)","type": "text", "default": "0.4"},
            "jitter":  {"label": "Jitter amount","type": "text", "default": "0.35"},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        vtype  = selection.x_type()
        df_work, sampled = self._large_data_sample(df, 50_000)
        series = self._to_mpl_numeric(df_work[col], vtype).dropna().values

        if len(series) == 0:
            ax.text(0.5, 0.5, "No numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        color = self._opt("color") or MPL_ACCENT
        try:
            alpha  = float(self._opt("alpha"))
        except (TypeError, ValueError):
            alpha = 0.4
        try:
            jitter_amt = float(self._opt("jitter"))
        except (TypeError, ValueError):
            jitter_amt = 0.35

        rng    = np.random.default_rng(42)
        jitter = rng.uniform(-jitter_amt, jitter_amt, size=len(series))

        ax.scatter(series, jitter, alpha=alpha, s=12, color=color, linewidths=0)
        ax.axhline(0, color="#CBD5E1", linewidth=0.8, zorder=0)
        ax.set_yticks([])
        ax.spines["left"].set_visible(False)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel(x_label)
        self._apply_title(ax, self._opt("title") or f"Strip Chart — {col}")
        self._apply_figure_style(fig, ax)
        if sampled:
            self._add_sample_note(ax, 50_000)
        fig.tight_layout()
