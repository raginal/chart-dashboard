"""
Donut Chart — univariate distribution.

• Nominal / Ordinal  → wedges per category, labelled with count & %
• Interval / Ratio   → auto-binned (up to 10 bins) and displayed as wedges
• Shows the top N categories; remainder collapsed into "Other"
"""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_DEFAULT_PALETTE, PALETTE_CHOICES

MAX_SLICES = 12   # more than this → collapse into "Other"


class DonutChart(BaseChart):
    CHART_ID       = "donut_chart"
    DISPLAY_NAME   = "Donut Chart"
    DIMENSIONALITY = "univariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":      {"label": "Title",         "type": "text",   "default": ""},
            "palette":    {"label": "Colour palette", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                           "choices": PALETTE_CHOICES},
            "show_pct":   {"label": "Show percentages","type": "bool",   "default": True},
            "show_count": {"label": "Show counts",    "type": "bool",   "default": False},
            "num_bins":   {"label": "Bins (numeric)", "type": "text",   "default": "8"},
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        col    = selection.x_var
        series = df[col].dropna()

        if series.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        var_type = selection.x_type()

        # ── Determine counts ──────────────────────────────────────────────────
        if var_type in (VariableType.INTERVAL, VariableType.DATE):
            # Numeric: bin the values
            numeric = pd.to_numeric(series, errors='coerce').dropna()
            if numeric.empty:
                ax.text(0.5, 0.5, "No numeric data to display.",
                        ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
                return
            try:
                n_bins = max(2, min(int(self._opt("num_bins") or 8), 20))
            except (TypeError, ValueError):
                n_bins = 8
            binned = pd.cut(numeric, bins=n_bins)
            counts = binned.value_counts().sort_index()
            labels = [str(b) for b in counts.index]
            values = counts.values.tolist()
        else:
            # Categorical / ordinal
            counts = series.astype(str).value_counts()
            if len(counts) > MAX_SLICES:
                top    = counts.head(MAX_SLICES - 1)
                other  = counts.iloc[MAX_SLICES - 1:].sum()
                counts = pd.concat([top, pd.Series({"Other": other})])
            labels = counts.index.tolist()
            values = counts.values.tolist()

        # ── Colours ───────────────────────────────────────────────────────────
        palette = self._opt("palette") or MPL_DEFAULT_PALETTE
        n = len(labels)
        try:
            cmap   = plt.cm.get_cmap(palette, max(n, 1))
            colors = [cmap(i / max(n - 1, 1)) for i in range(n)]
        except Exception:
            colors = ["#2563EB"] * n

        # ── Autopct string ────────────────────────────────────────────────────
        show_pct   = bool(self._opt("show_pct"))
        show_count = bool(self._opt("show_count"))
        total      = sum(values)

        def _autopct(pct):
            parts = []
            if show_pct:
                parts.append(f"{pct:.1f}%")
            if show_count:
                parts.append(f"n={int(round(pct * total / 100))}")
            return "\n".join(parts) if parts else ""

        # ── Draw ──────────────────────────────────────────────────────────────
        wedges, texts, autotexts = ax.pie(
            values,
            labels=labels,
            colors=colors,
            autopct=_autopct if (show_pct or show_count) else None,
            pctdistance=0.78,
            startangle=90,
            wedgeprops=dict(width=0.52, edgecolor="white", linewidth=1.5),
            textprops=dict(fontsize=9),
        )

        for at in (autotexts or []):
            at.set_fontsize(8)
            at.set_color("#1E293B")

        x_label = VariableTransformer.axis_label(col, selection.x_transform())
        ax.set_title(
            self._opt("title") or f"Distribution — {x_label}",
            fontsize=13, fontweight='bold', pad=14,
        )

        # Centre label showing total N
        ax.text(0, 0, f"n={total:,}", ha='center', va='center',
                fontsize=11, fontweight='600', color="#334155")

        self._apply_figure_style(fig, ax)
        fig.tight_layout()
