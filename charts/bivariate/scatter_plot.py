"""Scatter plot with optional trend line and Colour By support."""
from __future__ import annotations
import numpy as np
import pandas as pd
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Patch
from scipy import stats
from scipy.optimize import curve_fit

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT, MPL_TREND, MPL_DEFAULT_PALETTE


class ScatterPlot(BaseChart):
    CHART_ID       = "scatter_plot"
    DISPLAY_NAME   = "Scatter Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":       {"label": "Title",               "type": "text",   "default": ""},
            "x_label":     {"label": "X-axis label",         "type": "text",   "default": ""},
            "y_label":     {"label": "Y-axis label",         "type": "text",   "default": ""},
            "color":       {"label": "Point colour (no Z-Axis)", "type": "text",
                            "default": MPL_ACCENT},
            "palette":     {"label": "Z-Axis colour palette", "type": "choice", "default": MPL_DEFAULT_PALETTE,
                            "choices": ["tab10", "tab20", "Set1", "Set2", "viridis", "plasma",
                                        "Blues", "Greens", "RdBu_r", "coolwarm"]},
            "trend_line":  {"label": "Show trend line",     "type": "choice", "default": "None",
                            "choices": ["None", "Linear", "LOWESS", "Exponential"]},
            "trend_color": {"label": "Trend line colour",   "type": "text",   "default": MPL_TREND},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col      = selection.x_var
        y_col      = selection.y_var
        colour_var = selection.group_var   # Z-Axis drives scatter colouring
        x_type     = selection.x_type()
        y_type     = selection.y_type()

        # Build column list for subsetting
        cols = list({x_col, y_col} | ({colour_var} if colour_var else set()))
        df_work, sampled = self._large_data_sample(df, 50_000)

        sub = df_work[cols].copy()
        sub[x_col] = self._to_mpl_numeric(sub[x_col], x_type)
        sub[y_col] = self._to_mpl_numeric(sub[y_col], y_type)
        sub = sub.dropna(subset=[x_col, y_col])

        if sub.empty:
            ax.text(0.5, 0.5, "No numeric data to display.",
                    ha='center', va='center', transform=ax.transAxes, color="#94A3B8")
            return

        # ── Draw scatter ──────────────────────────────────────────────────────
        if colour_var and colour_var in sub.columns:
            self._scatter_by_colour(ax, sub, x_col, y_col, colour_var, fig)
        else:
            color = self._opt("color") or MPL_ACCENT
            ax.scatter(sub[x_col], sub[y_col], alpha=0.5, s=16,
                       color=color, linewidths=0, zorder=3)

        # ── Trend line ────────────────────────────────────────────────────────
        trend       = self._opt("trend_line") or "None"
        trend_color = self._opt("trend_color") or MPL_TREND

        if trend == "Linear":
            try:
                slope, intercept, r, p, _ = stats.linregress(sub[x_col], sub[y_col])
                xs = np.linspace(sub[x_col].min(), sub[x_col].max(), 200)
                ax.plot(xs, slope * xs + intercept, color=trend_color, linewidth=1.8,
                        label=f"r={r:.2f}, p={p:.3f}", zorder=4)
                ax.legend(fontsize=9, framealpha=0.8)
            except Exception:
                pass

        elif trend == "LOWESS":
            try:
                from statsmodels.nonparametric.smoothers_lowess import lowess
                smoothed = lowess(sub[y_col].values, sub[x_col].values, frac=0.4)
                smoothed_s = smoothed[np.argsort(smoothed[:, 0])]
                ax.plot(smoothed_s[:, 0], smoothed_s[:, 1], color=trend_color,
                        linewidth=1.8, label="LOWESS", zorder=4)
                ax.legend(fontsize=9, framealpha=0.8)
            except ImportError:
                pass

        elif trend == "Exponential":
            try:
                xs_arr    = sub[x_col].values.astype(float)
                ys_arr    = sub[y_col].values.astype(float)
                x_shift   = xs_arr.min()
                xs_shifted = xs_arr - x_shift
                if (ys_arr > 0).all():
                    def _exp_func(x, a, b):
                        return a * np.exp(b * x)
                    popt, _ = curve_fit(_exp_func, xs_shifted, ys_arr,
                                        p0=[ys_arr.mean(), 0.0], maxfev=5000)
                    xs_fit = np.linspace(xs_shifted.min(), xs_shifted.max(), 200)
                    ax.plot(xs_fit + x_shift, _exp_func(xs_fit, *popt),
                            color=trend_color, linewidth=1.8,
                            label="Exponential", zorder=4)
                    ax.legend(fontsize=9, framealpha=0.8)
                else:
                    ax.text(0.02, 0.97, "Exponential fit requires all Y > 0",
                            transform=ax.transAxes, fontsize=8,
                            color=trend_color, va='top')
            except Exception:
                pass

        # ── Date axis formatting ──────────────────────────────────────────────
        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)
        if y_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'y')

        # ── Labels & style ────────────────────────────────────────────────────
        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)
        self._apply_title(ax, self._opt("title") or f"{y_col} vs {x_col}")
        self._apply_figure_style(fig, ax)
        if sampled:
            self._add_sample_note(ax, 50_000)
        fig.tight_layout()

    # ── Colour-by helper ───────────────────────────────────────────────────────

    def _scatter_by_colour(self, ax, sub, x_col, y_col, colour_var, fig):
        """Colour points by colour_var — categorical → legend, numeric → colorbar."""
        colour_series = sub[colour_var]
        colour_numeric = pd.to_numeric(colour_series, errors='coerce')
        is_numeric = colour_numeric.notna().mean() >= 0.8

        if is_numeric:
            palette = self._opt("palette") or "viridis"
            sc = ax.scatter(sub[x_col], sub[y_col],
                            c=colour_numeric.fillna(colour_numeric.median()),
                            cmap=palette, alpha=0.6, s=16, linewidths=0, zorder=3)
            cb = fig.colorbar(sc, ax=ax, shrink=0.8)
            cb.set_label(colour_var, fontsize=9)
        else:
            # Categorical colour
            palette = self._opt("palette") or MPL_DEFAULT_PALETTE
            cats = colour_series.dropna().unique()
            try:
                cmap   = plt.cm.get_cmap(palette, max(len(cats), 1))
                colors = {cat: cmap(i / max(len(cats) - 1, 1))
                          for i, cat in enumerate(cats)}
            except Exception:
                colors = {cat: MPL_ACCENT for cat in cats}

            for cat, color in colors.items():
                mask = colour_series == cat
                ax.scatter(sub.loc[mask, x_col], sub.loc[mask, y_col],
                           alpha=0.55, s=16, color=color, linewidths=0, zorder=3,
                           label=str(cat))

            ax.legend(
                title=colour_var,
                fontsize=8,
                title_fontsize=9,
                loc='best',
                framealpha=0.85,
                markerscale=1.4,
            )
