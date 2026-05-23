"""Treemap using squarify."""
from __future__ import annotations
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.patches as mpatches
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES

try:
    import squarify
    _HAS_SQUARIFY = True
except ImportError:
    _HAS_SQUARIFY = False


class Treemap(BaseChart):
    CHART_ID       = "treemap"
    DISPLAY_NAME   = "Treemap"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",       "type": "text",   "default": ""},
            "palette": {"label": "Colour palette","type": "choice","default": MPL_DEFAULT_PALETTE,
                        "choices": PALETTE_CHOICES},
            "show_pct":{"label": "Show %",       "type": "bool",   "default": True},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        if not _HAS_SQUARIFY:
            ax.text(0.5, 0.5, "squarify is not installed.\nRun: pip install squarify",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8", fontsize=11)
            return

        x_col = selection.x_var   # categorical
        y_col = selection.y_var   # numeric (size of each tile)

        sub = df[[x_col, y_col]].copy()
        sub[y_col] = pd.to_numeric(sub[y_col], errors='coerce')
        sub = sub.dropna()
        sub = sub[sub[y_col] > 0]  # squarify requires positive values

        if sub.empty:
            ax.text(0.5, 0.5, "No positive numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        grouped = sub.groupby(x_col)[y_col].sum().sort_values(ascending=False)
        cats    = grouped.index.astype(str).tolist()
        sizes   = grouped.values.tolist()
        total   = sum(sizes)

        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        try:
            cmap   = plt.cm.get_cmap(palette, len(cats))
            colors = [cmap(i / max(len(cats)-1, 1)) for i in range(len(cats))]
        except Exception:
            colors = ["#2563EB"] * len(cats)

        labels = []
        for cat, sz in zip(cats, sizes):
            pct = sz / total * 100
            lbl = f"{cat}\n{sz:,.1f}" + (f"\n({pct:.1f}%)" if self._opt("show_pct") else "")
            labels.append(lbl)

        squarify.plot(sizes=sizes, label=labels, color=colors,
                      alpha=0.85, ax=ax, text_kwargs={"fontsize": 8, "wrap": True})
        ax.set_axis_off()
        ax.set_title(self._opt("title") or f"{y_col} by {x_col}", fontsize=13, fontweight='bold', pad=10)
        fig.patch.set_facecolor("white")
        fig.tight_layout()
