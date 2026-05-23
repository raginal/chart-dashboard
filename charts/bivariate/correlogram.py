"""
Correlogram — correlation matrix heatmap.

Shows the pairwise Pearson correlation between the selected X and Y variables,
plus any other numeric columns in the dataset (up to 15).
"""
from __future__ import annotations
import pandas as pd
import seaborn as sns
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from ui.palette import PALETTE_CHOICES


class Correlogram(BaseChart):
    CHART_ID       = "correlogram"
    DISPLAY_NAME   = "Correlogram"
    DIMENSIONALITY = "bivariate"

    # Maximum number of columns shown in the matrix
    MAX_COLS = 15

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":    {"label": "Title",       "type": "text",   "default": ""},
            "palette":  {"label": "Colour map",  "type": "choice", "default": "RdBu_r",
                         "choices": PALETTE_CHOICES},
            "annot":    {"label": "Show values",  "type": "bool",   "default": True},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        # Collect numeric columns; prioritise x and y, then fill up to MAX_COLS
        x_col = selection.x_var
        y_col = selection.y_var
        numeric_cols = [
            c for c in df.columns
            if pd.api.types.is_numeric_dtype(df[c])
        ]

        # Prioritise selected vars, then fill
        prioritised = [c for c in [x_col, y_col] if c in numeric_cols]
        remaining   = [c for c in numeric_cols if c not in prioritised]
        cols        = (prioritised + remaining)[:self.MAX_COLS]

        if len(cols) < 2:
            ax.text(0.5, 0.5, "Need at least 2 numeric columns for a correlogram.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        corr = df[cols].apply(pd.to_numeric, errors='coerce').corr()
        palette = self._opt("palette") or "RdBu_r"
        annot   = bool(self._opt("annot"))

        mask = None  # show full matrix
        sns.heatmap(
            corr, ax=ax,
            cmap=palette,
            vmin=-1, vmax=1,
            center=0,
            annot=annot,
            fmt=".2f" if annot else "",
            annot_kws={"size": 8},
            linewidths=0.5,
            linecolor="#E2E8F0",
            square=True,
            cbar_kws={"shrink": 0.8},
        )
        ax.set_title(self._opt("title") or "Correlation Matrix", fontsize=13, fontweight='bold', pad=10)
        ax.tick_params(axis='x', rotation=45, labelsize=9)
        ax.tick_params(axis='y', rotation=0,  labelsize=9)
        fig.patch.set_facecolor("white")
        fig.tight_layout()
