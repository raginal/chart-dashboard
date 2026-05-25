"""
Heatmap — cell values can be counts (categorical × categorical) or
mean of a third numeric variable (any combination).
"""
from __future__ import annotations
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import PALETTE_CHOICES


class Heatmap(BaseChart):
    CHART_ID       = "heatmap"
    DISPLAY_NAME   = "Heatmap"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text",   "default": ""},
            "x_label": {"label": "X-axis label", "type": "text",   "default": ""},
            "y_label": {"label": "Y-axis label", "type": "text",   "default": ""},
            "palette": {"label": "Colour map",   "type": "choice", "default": "Blues",
                        "choices": PALETTE_CHOICES},
            "annot":   {"label": "Show values",  "type": "bool",   "default": True},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var
        # Use group_var (Z-Axis) as the value variable if numeric, else use counts
        grp_col = selection.group_var

        cols_needed = [c for c in [x_col, y_col, grp_col] if c]
        sub = df[cols_needed].dropna()

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        # Determine pivot value
        if grp_col:
            grp_numeric = pd.to_numeric(sub[grp_col], errors='coerce')
            if grp_numeric.notna().mean() >= 0.8:
                sub = sub.copy()
                sub[grp_col] = grp_numeric
                pivot = sub.pivot_table(index=y_col, columns=x_col,
                                        values=grp_col, aggfunc='mean')
                cbar_label = f"Mean {grp_col}"
            else:
                # Count pivot
                pivot = sub.groupby([y_col, x_col]).size().unstack(fill_value=0)
                cbar_label = "Count"
        else:
            pivot = sub.groupby([y_col, x_col]).size().unstack(fill_value=0)
            cbar_label = "Count"

        if pivot.empty or pivot.shape[0] == 0 or pivot.shape[1] == 0:
            ax.text(0.5, 0.5, "Not enough variation to build a heatmap.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        palette = self._opt("palette") or "Blues"
        annot   = bool(self._opt("annot"))

        # Limit size for readability
        MAX_ROWS, MAX_COLS = 30, 30
        pivot = pivot.iloc[:MAX_ROWS, :MAX_COLS]

        sns.heatmap(pivot, ax=ax, cmap=palette, annot=annot,
                    fmt=".1f" if annot else "",
                    annot_kws={"size": 8},
                    linewidths=0.3, linecolor="#E2E8F0",
                    cbar_kws={"label": cbar_label, "shrink": 0.8})

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        self._apply_title(ax, self._opt("title") or "Heatmap")
        self._apply_figure_style(fig, ax, grid=False)
        ax.tick_params(axis='x', rotation=45, labelsize=8)
        ax.tick_params(axis='y', rotation=0,  labelsize=8)
        fig.tight_layout()
