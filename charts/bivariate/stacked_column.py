"""
Stacked Column Chart — stacked bars for two categorical variables.

Only shown for categorical × categorical pairs (both X and Y must be
Nominal or Ordinal).  Bars represent counts per X × Y combination,
optionally normalised to 100%.
"""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES


class StackedColumn(BaseChart):
    CHART_ID       = "stacked_column"
    DISPLAY_NAME   = "Stacked Column Chart"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":     {"label": "Title",           "type": "text",   "default": ""},
            "x_label":   {"label": "X-axis label",     "type": "text",   "default": ""},
            "y_label":   {"label": "Y-axis label",     "type": "text",   "default": "Count"},
            "palette":   {"label": "Colour palette",   "type": "choice", "default": MPL_DEFAULT_PALETTE,
                          "choices": PALETTE_CHOICES},
            "normalize": {"label": "100% stacked",     "type": "bool",   "default": False},
            "rotate_x":  {"label": "Rotate X labels",  "type": "bool",   "default": False},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var
        df_work = df[[x_col, y_col]].dropna().copy()
        df_work[x_col] = df_work[x_col].astype(str)
        df_work[y_col] = df_work[y_col].astype(str)

        if df_work.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        # Pivot: rows = X categories, columns = Y categories, values = counts
        counts = df_work.groupby(x_col)[y_col].value_counts().unstack(fill_value=0)

        if self._opt("normalize"):
            counts = counts.div(counts.sum(axis=1), axis=0) * 100

        n_y = len(counts.columns)
        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        try:
            cmap   = plt.cm.get_cmap(palette, max(n_y, 2))
            colors = [cmap(i / max(n_y - 1, 1)) for i in range(n_y)]
        except Exception:
            colors = None

        counts.plot(kind='bar', stacked=True, ax=ax,
                    color=colors, legend=True, width=0.65)

        x_cats = counts.index.astype(str).tolist()
        rotate = bool(self._opt("rotate_x")) or len(x_cats) > 8
        ax.set_xticklabels(x_cats,
                           rotation=45 if rotate else 0,
                           ha='right' if rotate else 'center')

        ax.legend(title=y_col, fontsize=8, title_fontsize=9,
                  loc='best', framealpha=0.85)
        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        ax.set_xlabel(x_label)
        if self._opt("normalize"):
            ax.set_ylabel("Percentage (%)")
        else:
            ax.set_ylabel(self._opt("y_label") or "Count")
        self._apply_title(ax, self._opt("title") or f"{y_col} by {x_col} (Stacked)")
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
