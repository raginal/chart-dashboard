"""
Histogram with Freedman-Diaconis automatic bin sizing.

Falls back to Sturges' rule when IQR == 0 (all values identical or near-identical).
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class Histogram(BaseChart):
    CHART_ID       = "histogram"
    DISPLAY_NAME   = "Histogram"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text", "default": ""},
            "x_label": {"label": "X-axis label", "type": "text", "default": ""},
            "y_label": {"label": "Y-axis label", "type": "text", "default": "Count"},
            "color":   {"label": "Bar colour",   "type": "text", "default": MPL_ACCENT},
            "show_kde":{"label": "Overlay KDE",  "type": "bool", "default": False},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        vtype  = selection.x_type()
        series = self._to_mpl_numeric(df[col], vtype).dropna().values

        if len(series) < 2:
            ax.text(0.5, 0.5, "Not enough data for a histogram.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        n_bins = self._freedman_diaconis_bins(series)
        color  = self._opt("color") or MPL_ACCENT

        ax.hist(series, bins=n_bins, color=color, alpha=0.75,
                edgecolor="white", linewidth=0.5, zorder=2)

        if self._opt("show_kde"):
            from scipy.stats import gaussian_kde
            kde = gaussian_kde(series)
            xs  = np.linspace(series.min(), series.max(), 300)
            # Scale KDE to count axis
            bin_width = (series.max() - series.min()) / n_bins
            ax2 = ax.twinx()
            ax2.plot(xs, kde(xs), color="#DC2626", linewidth=1.5, label="KDE")
            ax2.set_ylabel("Density", color="#DC2626", fontsize=10)
            ax2.tick_params(axis='y', colors="#DC2626")
            ax2.spines["right"].set_color("#DC2626")
            ax2.set_ylim(bottom=0)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        y_label = self._opt("y_label") or "Count"
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        self._apply_title(ax, self._opt("title") or f"Histogram — {col}")
        self._apply_figure_style(fig, ax)
        fig.tight_layout()

    @staticmethod
    def _freedman_diaconis_bins(data: np.ndarray) -> int:
        """
        Compute optimal number of bins using the Freedman-Diaconis rule:
            bin_width = 2 × IQR × n^(-1/3)
        Falls back to Sturges' rule when IQR == 0.
        """
        n = len(data)
        q75, q25 = np.percentile(data, [75, 25])
        iqr = q75 - q25
        data_range = data.max() - data.min()

        if iqr > 0 and data_range > 0:
            bin_width = 2.0 * iqr / (n ** (1 / 3))
            n_bins = int(np.ceil(data_range / bin_width))
        else:
            # Sturges fallback
            n_bins = int(np.ceil(np.log2(n) + 1))

        # Reasonable guard rails
        return max(1, min(n_bins, 200))
