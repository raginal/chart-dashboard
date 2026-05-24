"""Box Plot — univariate (single numeric) or bivariate (numeric Y grouped by categorical X)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class BoxPlot(BaseChart):
    CHART_ID       = "box_plot"
    DISPLAY_NAME   = "Box Plot"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":       {"label": "Title",        "type": "text", "default": ""},
            "x_label":     {"label": "X-axis label",  "type": "text", "default": ""},
            "show_points": {"label": "Show points",   "type": "bool", "default": False},
            "color":       {"label": "Box colour",    "type": "text", "default": MPL_ACCENT},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col  = selection.x_var
        y_col  = selection.y_var
        x_type = selection.x_type()

        _is_cat = x_type in (VariableType.NOMINAL, VariableType.ORDINAL, VariableType.LOCATION)

        # ── Bivariate mode: categorical/location X, numeric Y ─────────────────
        if y_col is not None and _is_cat:
            self._render_grouped(df, ax, x_col, y_col, selection)
        else:
            # ── Univariate mode: single numeric variable ──────────────────────
            self._render_single(df, ax, x_col, selection)

        self._apply_figure_style(fig, ax)
        fig.tight_layout()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _render_single(self, df, ax, col, selection):
        vtype  = selection.x_type()
        series = self._to_mpl_numeric(df[col], vtype).dropna()
        if series.empty:
            ax.text(0.5, 0.5, "No numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        color = self._opt("color") or MPL_ACCENT
        ax.boxplot(series, vert=True, patch_artist=True,
                   boxprops=dict(facecolor=color, alpha=0.7),
                   medianprops=dict(color="#0F172A", linewidth=2),
                   whiskerprops=dict(color="#334155"),
                   capprops=dict(color="#334155"),
                   flierprops=dict(marker='o', markerfacecolor=color,
                                   markersize=4, alpha=0.5, linestyle='none'))

        if self._opt("show_points"):
            jitter = np.random.uniform(-0.08, 0.08, size=len(series))
            ax.scatter(1 + jitter, series.values, alpha=0.3, s=8,
                       color="#334155", zorder=3)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'y')
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel("Value")
        ax.set_xticklabels([x_label])
        ax.set_title(self._opt("title") or f"Box Plot — {col}",
                     fontsize=13, fontweight='bold', pad=10)

    def _render_grouped(self, df, ax, x_col, y_col, selection):
        """Box per category of x_col, values = y_col — single colour."""
        cats = sorted(df[x_col].dropna().unique(), key=str)
        MAX_CATS = 30
        if len(cats) > MAX_CATS:
            cats = cats[:MAX_CATS]

        groups, labels = [], []
        for cat in cats:
            mask = df[x_col].astype(str) == str(cat)
            vals = pd.to_numeric(df.loc[mask, y_col], errors='coerce').dropna()
            if len(vals) > 0:
                groups.append(vals.values)
                labels.append(str(cat))

        if not groups:
            ax.text(0.5, 0.5, "No numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        color = self._opt("color") or MPL_ACCENT

        bp = ax.boxplot(groups, vert=True, patch_artist=True,
                        medianprops=dict(color="#0F172A", linewidth=2),
                        whiskerprops=dict(color="#475569"),
                        capprops=dict(color="#475569"),
                        flierprops=dict(marker='o', markersize=4, alpha=0.5, linestyle='none'))

        for patch in bp['boxes']:
            patch.set_facecolor(color)
            patch.set_alpha(0.75)
        for flier in bp['fliers']:
            flier.set_markerfacecolor(color)

        if self._opt("show_points"):
            for i, group in enumerate(groups):
                jitter = np.random.uniform(-0.12, 0.12, size=len(group))
                ax.scatter(i + 1 + jitter, group, alpha=0.25, s=6,
                           color=color, zorder=3)

        ax.set_xticks(range(1, len(labels) + 1))
        ax.set_xticklabels(labels, rotation=45, ha='right', fontsize=9)
        ax.set_xlabel(self._opt("x_label") or x_col)
        ax.set_ylabel(VariableTransformer.axis_label(y_col, selection.y_transform()))
        ax.set_title(self._opt("title") or f"{y_col} by {x_col}",
                     fontsize=13, fontweight='bold', pad=10)
