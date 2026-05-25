"""
Small Multiples — faceted grid of scatter or line sub-charts.

Lives in the **trivariate** tab (requires X + Y + Z-Axis).

The Z-Axis variable is the facet variable.  Each panel shows X vs Y for one
value of Z.  Facet sort order, sub-chart type, shared axes, colour palette,
and (for Scatter) trend lines are all configurable via Quick Edit.
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
from ui.palette import MPL_ACCENT, MPL_TREND, MPL_DEFAULT_PALETTE, PALETTE_CHOICES

MAX_FACETS = 16


class SmallMultiples(BaseChart):
    CHART_ID       = "small_multiples"
    DISPLAY_NAME   = "Small Multiples"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":       {"label": "Title",                     "type": "text",   "default": ""},
            "chart_type":  {"label": "Sub-chart type",            "type": "choice", "default": "Scatter",
                            "choices": ["Scatter", "Line"]},
            "palette":     {"label": "Colour palette",            "type": "choice", "default": MPL_DEFAULT_PALETTE,
                            "choices": PALETTE_CHOICES},
            "same_color":  {"label": "Same colour",               "type": "bool",   "default": True},
            "shared_axes": {"label": "Shared axis ranges",        "type": "bool",   "default": True},
            "ncols":       {"label": "Columns",                   "type": "text",   "default": "3"},
            "sort_order":  {"label": "Facet order",               "type": "choice", "default": "Ascending",
                            "choices": ["Ascending", "Descending", "As-is"]},
            # Scatter-only options (hidden automatically when chart_type == "Line")
            "trend_line":  {"label": "Trend line",   "type": "choice", "default": "None",
                            "choices": ["None", "Linear", "LOWESS", "Exponential"]},
            "trend_color": {"label": "Trend colour", "type": "text",   "default": MPL_TREND},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()

        x_col   = selection.x_var
        y_col   = selection.y_var
        fac_col = selection.group_var

        if fac_col is None:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "Select a Z-Axis variable to facet by.",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        sub = df[[x_col, y_col, fac_col]].dropna()

        if sub.empty:
            ax = fig.add_subplot(111)
            ax.text(0.5, 0.5, "No data after removing missing values.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Sort facets ───────────────────────────────────────────────────────
        sort_order = self._opt("sort_order") or "Ascending"
        raw_facets = sub[fac_col].unique().tolist()
        if sort_order == "Ascending":
            try:
                facets = sorted(raw_facets)
            except TypeError:
                facets = sorted(raw_facets, key=str)
        elif sort_order == "Descending":
            try:
                facets = sorted(raw_facets, reverse=True)
            except TypeError:
                facets = sorted(raw_facets, key=str, reverse=True)
        else:
            facets = raw_facets

        if len(facets) > MAX_FACETS:
            facets = facets[:MAX_FACETS]

        try:
            ncols = max(1, min(int(self._opt("ncols") or 3), len(facets)))
        except (TypeError, ValueError):
            ncols = 3

        nrows      = int(np.ceil(len(facets) / ncols))
        chart_type = self._opt("chart_type") or "Scatter"

        palette   = self._opt("palette") or MPL_DEFAULT_PALETTE
        same_color = self._opt("same_color")
        same_color = True if same_color is None else bool(same_color)
        try:
            cmap = plt.cm.get_cmap(palette, max(len(facets), 2))
            if same_color:
                colors = [cmap(0.0)] * len(facets)
            else:
                colors = [cmap(i / max(len(facets) - 1, 1)) for i in range(len(facets))]
        except Exception:
            colors = [MPL_ACCENT] * len(facets)

        shared_axes = self._opt("shared_axes")
        shared_axes = True if shared_axes is None else bool(shared_axes)
        axes = fig.subplots(nrows, ncols, squeeze=False,
                            sharex=shared_axes, sharey=shared_axes)

        x_type = selection.x_type()
        y_type = selection.y_type()

        trend       = self._opt("trend_line") or "None"
        trend_color = self._opt("trend_color") or MPL_TREND

        # Bottom-left panel index: used to limit redundant LOWESS/Exp legends
        bottom_left_idx = (nrows - 1) * ncols

        for idx, (facet, color) in enumerate(zip(facets, colors)):
            row, col = divmod(idx, ncols)
            ax = axes[row][col]
            mask = sub[fac_col] == facet
            xs   = self._to_mpl_numeric(sub.loc[mask, x_col], x_type)
            ys   = self._to_mpl_numeric(sub.loc[mask, y_col], y_type)

            if chart_type == "Scatter":
                valid = xs.notna() & ys.notna()
                ax.scatter(xs[valid], ys[valid], color=color, alpha=0.6, s=14, linewidths=0)

                # ── Per-panel trend line ──────────────────────────────────────
                if trend != "None":
                    xv = xs[valid].values.astype(float)
                    yv = ys[valid].values.astype(float)
                    # LOWESS / Exponential: show legend only on bottom-left panel
                    # Linear: always show (r value is informative per panel)
                    show_legend = (trend == "Linear") or (idx == bottom_left_idx)
                    self._draw_trend(ax, xv, yv, trend, trend_color,
                                     show_legend=show_legend)

            elif chart_type == "Line":
                valid = xs.notna() & ys.notna()
                order = xs[valid].argsort()
                ax.plot(xs[valid].iloc[order], ys[valid].iloc[order],
                        color=color, linewidth=1.5)

            ax.set_title(str(facet), fontsize=9, fontweight='bold', pad=4,
                         color=self._text_color())
            ax.spines["top"].set_visible(False)
            ax.spines["right"].set_visible(False)
            ax.spines["left"].set_color(self._spine_color())
            ax.spines["bottom"].set_color(self._spine_color())
            ax.tick_params(colors=self._text_color(), labelsize=8)
            ax.set_facecolor(self._chart_bg())

        # Apply date formatters to shared axes
        if len(facets) > 0:
            ref_ax = axes[0][0]
            if x_type == VariableType.DATE:
                self._apply_date_fmt(ref_ax, 'x', fig)
            if y_type == VariableType.DATE:
                self._apply_date_fmt(ref_ax, 'y')

        # Hide unused panels
        for idx in range(len(facets), nrows * ncols):
            row, col = divmod(idx, ncols)
            axes[row][col].set_visible(False)

        x_label = VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = VariableTransformer.axis_label(y_col, selection.y_transform())
        title   = self._opt("title") or f"{y_col} vs {x_col} — faceted by {fac_col}"

        fig.tight_layout(rect=[0.03, 0.04, 1.0, 0.93])
        self._apply_suptitle(fig, title)
        fig.supxlabel(x_label, fontsize=10, y=0.01, color=self._text_color())
        fig.supylabel(y_label, fontsize=10, x=0.0, color=self._text_color())
        fig.patch.set_facecolor(self._chart_bg())

        # ── Edit dialog visibility ────────────────────────────────────────────
        is_scatter = chart_type == "Scatter"
        self._set_visible("trend_line",  is_scatter)
        self._set_visible("trend_color", is_scatter)

    # ── Trend line helper ──────────────────────────────────────────────────────

    def _draw_trend(self, ax, xv: np.ndarray, yv: np.ndarray,
                    trend: str, color: str, show_legend: bool = True) -> None:
        """Draw a trend line onto *ax*.  Silently skips if data is insufficient.

        show_legend controls whether a legend entry is added.  For Linear the
        r-value is informative per panel so it is always shown.  For LOWESS and
        Exponential the label is the same on every panel, so callers pass
        show_legend=False on all panels except the bottom-left one.
        """
        if len(xv) < 3:
            return
        try:
            if trend == "Linear":
                from scipy import stats
                slope, intercept, r, p, _ = stats.linregress(xv, yv)
                xs_fit = np.linspace(xv.min(), xv.max(), 200)
                ax.plot(xs_fit, slope * xs_fit + intercept,
                        color=color, linewidth=1.4,
                        label=f"r={r:.2f}", zorder=4)
                ax.legend(fontsize=7, framealpha=0.8)

            elif trend == "LOWESS":
                from statsmodels.nonparametric.smoothers_lowess import lowess
                smoothed = lowess(yv, xv, frac=0.4)
                smoothed_s = smoothed[np.argsort(smoothed[:, 0])]
                ax.plot(smoothed_s[:, 0], smoothed_s[:, 1],
                        color=color, linewidth=1.4,
                        label="LOWESS" if show_legend else "_nolegend_", zorder=4)
                if show_legend:
                    ax.legend(fontsize=7, framealpha=0.8)

            elif trend == "Exponential":
                from scipy.optimize import curve_fit
                x_shift    = xv.min()
                xs_shifted = xv - x_shift
                if (yv > 0).all():
                    def _exp_func(x, a, b):
                        return a * np.exp(b * x)
                    popt, _ = curve_fit(_exp_func, xs_shifted, yv,
                                        p0=[yv.mean(), 0.0], maxfev=5000)
                    xs_fit = np.linspace(xs_shifted.min(), xs_shifted.max(), 200)
                    ax.plot(xs_fit + x_shift, _exp_func(xs_fit, *popt),
                            color=color, linewidth=1.4,
                            label="Exp" if show_legend else "_nolegend_", zorder=4)
                    if show_legend:
                        ax.legend(fontsize=7, framealpha=0.8)
        except Exception:
            pass   # silently skip if trend cannot be computed for this panel
