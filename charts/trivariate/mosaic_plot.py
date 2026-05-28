"""
Mosaic Plot — proportional area view of two categorical variables.

Lives in the **bivariate** tab (cat × cat).
Cell labels show count + percentage.
"""
from __future__ import annotations
import matplotlib.pyplot as plt
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES


class MosaicPlot(BaseChart):
    CHART_ID       = "mosaic_plot"
    DISPLAY_NAME   = "Mosaic Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",         "type": "text",   "default": ""},
            "palette":    {"label": "Colour palette", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                           "choices": PALETTE_CHOICES},
            "show_counts":{"label": "Show counts",   "type": "bool",   "default": True},
            "show_pct":   {"label": "Show %",         "type": "bool",   "default": True},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()

        x_col = selection.x_var
        y_col = selection.y_var

        sub = df[[x_col, y_col]].dropna().copy()
        sub[x_col] = sub[x_col].astype(str)
        sub[y_col] = sub[y_col].astype(str)

        if sub.empty:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        try:
            from statsmodels.graphics.mosaicplot import mosaic
        except ImportError:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "statsmodels is required for mosaic plots.\n"
                               "Run: pip install statsmodels",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        # ── Colour mapping: one colour per Y category, consistent across X ─────
        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        cats_x  = sorted(sub[x_col].unique(), key=str)
        cats_y  = sorted(sub[y_col].unique(), key=str)
        n_cats_y = max(len(cats_y), 1)
        try:
            cmap   = plt.cm.get_cmap(palette, max(n_cats_y, 2))
            colors = [cmap(i / max(n_cats_y - 1, 1)) for i in range(n_cats_y)]
        except Exception:
            colors = ["#2563EB"] * n_cats_y

        # Each Y category gets a fixed colour; that colour is used for every X panel.
        color_map: dict[tuple, str] = {}
        for j, cy in enumerate(cats_y):
            c = colors[j % len(colors)]
            for cx in cats_x:
                color_map[(cx, cy)] = c

        # ── Count lookup for labels ───────────────────────────────────────────
        count_series = sub.groupby([x_col, y_col]).size()
        total        = len(sub)

        show_counts = bool(self._opt("show_counts"))
        show_pct    = bool(self._opt("show_pct"))

        def labelizer(k: tuple) -> str:
            if not (show_counts or show_pct):
                return ""
            try:
                n = int(count_series.get(k, 0))
            except Exception:
                return ""
            if n == 0:
                return ""
            parts: list[str] = []
            if show_counts:
                parts.append(f"{n:,}")
            if show_pct and total > 0:
                parts.append(f"{n / total * 100:.0f}%")
            return "\n".join(parts)

        # ── Draw ─────────────────────────────────────────────────────────────
        ax    = fig.add_subplot(111)
        title = self._opt("title") or f"{y_col} by {x_col}"

        x_rot = 45.0 if (len(cats_x) > 6 or max((len(s) for s in cats_x), default=0) > 8) else 0.0
        try:
            mosaic(
                sub,
                [x_col, y_col],
                ax=ax,
                horizontal=True,
                gap=0.018,
                properties=lambda key: {
                    "color": color_map.get(key, "#E2E8F0"),
                    "alpha": 1.0,
                },
                labelizer=labelizer,
                axes_label=True,
                label_rotation=[x_rot, 0.0],
            )
        except Exception as exc:
            fig.clear()
            ax2 = fig.add_subplot(111)
            ax2.text(0.5, 0.5, f"Could not render mosaic plot:\n{exc}",
                     ha="center", va="center", transform=ax2.transAxes,
                     color="#94A3B8", fontsize=10, wrap=True)

        # Style the axes text produced by statsmodels
        for text_obj in ax.texts:
            text_obj.set_fontsize(8)
            text_obj.set_color("#1E293B")

        self._apply_title(ax, title)

        fig.patch.set_facecolor(self._chart_bg())
        try:
            fig.tight_layout()
        except Exception:
            pass
