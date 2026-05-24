"""Violin Plot — univariate (single numeric) or bivariate (numeric Y grouped by categorical X)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class ViolinPlot(BaseChart):
    CHART_ID       = "violin_plot"
    DISPLAY_NAME   = "Violin Plot"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":    {"label": "Title",        "type": "text", "default": ""},
            "x_label":  {"label": "X-axis label",  "type": "text", "default": ""},
            "show_box": {"label": "Show inner box", "type": "bool", "default": True},
            "color":    {"label": "Violin colour",  "type": "text", "default": MPL_ACCENT},
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
            self._render_single(df, ax, x_col, selection)

        self._apply_figure_style(fig, ax)
        fig.tight_layout()

    # ── Private helpers ────────────────────────────────────────────────────────

    def _render_single(self, df, ax, col, selection):
        vtype   = selection.x_type()
        df_work, sampled = self._large_data_sample(df, 50_000)
        series  = self._to_mpl_numeric(df_work[col], vtype).dropna()

        if len(series) < 3:
            ax.text(0.5, 0.5, "Not enough data for a violin plot (need ≥ 3 values).",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        color = self._opt("color") or MPL_ACCENT
        parts = ax.violinplot([series.values], positions=[1],
                              showmeans=False, showmedians=True, showextrema=True)
        for pc in parts['bodies']:
            pc.set_facecolor(color)
            pc.set_alpha(0.7)
        for part_name in ('cbars', 'cmins', 'cmaxes', 'cmedians'):
            if part_name in parts:
                parts[part_name].set_color("#334155")

        if self._opt("show_box"):
            q1, med, q3 = np.percentile(series, [25, 50, 75])
            ax.vlines(1, q1, q3, color="#0F172A", linewidth=5, zorder=4)
            ax.scatter([1], [med], color="white", s=16, zorder=5)

        if vtype == VariableType.DATE:
            self._apply_date_fmt(ax, 'y')
        x_label = self._opt("x_label") or VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_xticks([1])
        ax.set_xticklabels([x_label])
        ax.set_ylabel("Value")
        ax.set_title(self._opt("title") or f"Violin Plot — {col}",
                     fontsize=13, fontweight='bold', pad=10)

        if sampled:
            self._add_sample_note(ax, 50_000)

    def _render_grouped(self, df, ax, x_col, y_col, selection):
        """One violin per category of x_col — single colour."""
        df_work, sampled = self._large_data_sample(df, 50_000)
        cats = sorted(df_work[x_col].dropna().unique(), key=str)
        MAX_CATS = 20
        if len(cats) > MAX_CATS:
            cats = cats[:MAX_CATS]

        groups, positions, labels = [], [], []
        for i, cat in enumerate(cats):
            mask = df_work[x_col].astype(str) == str(cat)
            vals = pd.to_numeric(df_work.loc[mask, y_col], errors='coerce').dropna()
            if len(vals) >= 3:
                groups.append(vals.values)
                positions.append(i + 1)
                labels.append(str(cat))

        if not groups:
            ax.text(0.5, 0.5, "Not enough data for grouped violin (need ≥ 3 values per group).",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        color = self._opt("color") or MPL_ACCENT

        parts = ax.violinplot(groups, positions=positions,
                              showmeans=False, showmedians=True, showextrema=True)

        for pc in parts['bodies']:
            pc.set_facecolor(color)
            pc.set_alpha(0.75)
        for part_name in ('cbars', 'cmins', 'cmaxes', 'cmedians'):
            if part_name in parts:
                parts[part_name].set_color("#334155")

        if self._opt("show_box"):
            for i, group in enumerate(groups):
                q1, med, q3 = np.percentile(group, [25, 50, 75])
                ax.vlines(positions[i], q1, q3, color="#0F172A", linewidth=4, zorder=4)
                ax.scatter([positions[i]], [med], color="white", s=12, zorder=5)

        ax.set_xticks(positions)
        n        = len(labels)
        max_len  = max((len(str(l)) for l in labels), default=0)
        # Rotate only when labels would likely overlap: product of count × longest
        # label > 80, or too many categories regardless of label length.
        rotate   = (n * max_len) > 80 or n > 12
        ax.set_xticklabels(
            labels,
            rotation=45 if rotate else 0,
            ha='right' if rotate else 'center',
            fontsize=max(6, 9 - max(n - 8, 0) // 3),
        )
        ax.set_xlabel(self._opt("x_label") or x_col)
        ax.set_ylabel(VariableTransformer.axis_label(y_col, selection.y_transform()))
        ax.set_title(self._opt("title") or f"{y_col} by {x_col}",
                     fontsize=13, fontweight='bold', pad=10)

        if sampled:
            self._add_sample_note(ax, 50_000)
