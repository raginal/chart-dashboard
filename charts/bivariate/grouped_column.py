"""Grouped column chart with optional error bars."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES


class GroupedColumn(BaseChart):
    CHART_ID       = "grouped_column"
    DISPLAY_NAME   = "Grouped Column Chart"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",        "type": "text",   "default": ""},
            "x_label":    {"label": "X-axis label",  "type": "text",   "default": ""},
            "y_label":    {"label": "Y-axis label",  "type": "text",   "default": "Count"},
            "palette":    {"label": "Colour palette","type": "choice", "default": MPL_DEFAULT_PALETTE,
                           "choices": PALETTE_CHOICES},
            "error_bars": {"label": "Show error bars","type": "bool",  "default": False},
            "rotate_x":   {"label": "Rotate X labels","type": "bool",  "default": False},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var
        df_work = df[[x_col, y_col]].dropna()

        if df_work.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        y_type    = selection.y_type()
        y_numeric = pd.to_numeric(df_work[y_col], errors='coerce')
        _use_numeric = (
            y_type in (VariableType.INTERVAL, VariableType.DATE)
            or (
                y_type not in (VariableType.NOMINAL, VariableType.ORDINAL)
                and y_numeric.notna().mean() >= 0.8
            )
        )
        if _use_numeric:
            # Numeric Y: plot mean per category
            df_work = df_work.copy()
            df_work[y_col] = y_numeric
            grouped = df_work.groupby(x_col)[y_col]
            means  = grouped.mean()
            sems   = grouped.sem()
            cats   = means.index.astype(str).tolist()
            x_pos  = np.arange(len(cats))
            palette = self._opt("palette") or MPL_DEFAULT_PALETTE
            import matplotlib.pyplot as plt
            colors = plt.cm.get_cmap(palette, len(cats)) if len(cats) > 1 else [self._opt("palette") or "#2563EB"]
            try:
                bar_colors = [colors(i / max(len(cats)-1, 1)) for i in range(len(cats))]
            except TypeError:
                bar_colors = [colors] * len(cats)
            yerr = sems.values if self._opt("error_bars") else None
            ax.bar(x_pos, means.values, color=bar_colors, width=0.65,
                   yerr=yerr, capsize=4, error_kw={"ecolor": "#334155", "linewidth": 1},
                   zorder=2)
            ax.set_xticks(x_pos)
            y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        else:
            # Categorical Y: count occurrences
            counts = df_work.groupby(x_col)[y_col].value_counts().unstack(fill_value=0)
            counts.plot(kind='bar', ax=ax, legend=True)
            cats = counts.index.astype(str).tolist()
            x_pos = np.arange(len(cats))
            y_label = "Count"

        ax.set_xticklabels(cats, rotation=(45 if self._opt("rotate_x") else 0),
                           ha='right' if self._opt("rotate_x") else 'center')
        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(self._opt("y_label") or y_label)
        ax.set_title(self._opt("title") or f"{y_col} by {x_col}", fontsize=13, fontweight='bold', pad=10)
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
