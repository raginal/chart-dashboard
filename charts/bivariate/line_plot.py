"""Line plot with optional confidence band (95% CI via bootstrapping or SEM)."""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT, MPL_CONFIDENCE_BAND


class LinePlot(BaseChart):
    CHART_ID       = "line_plot"
    DISPLAY_NAME   = "Line Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":     {"label": "Title",              "type": "text", "default": ""},
            "x_label":   {"label": "X-axis label",        "type": "text", "default": ""},
            "y_label":   {"label": "Y-axis label",        "type": "text", "default": ""},
            "color":     {"label": "Y line colour",       "type": "text", "default": MPL_ACCENT},
            "z_color":   {"label": "Z line colour",       "type": "text", "default": "#DC2626"},
            "conf_band": {"label": "Confidence band",     "type": "bool", "default": False},
            "markers":   {"label": "Show data markers",   "type": "bool", "default": False},
            "sort_x":    {"label": "Sort by X",           "type": "bool", "default": True},
            **BaseChart._title_style_options(),
        }

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col  = selection.x_var
        y_col  = selection.y_var
        z_col  = selection.group_var   # numeric Z → second line (trivariate mode)
        x_type = selection.x_type()
        z_type = selection.group_type()

        # Determine whether Z provides a second numeric line
        z_is_line = (
            z_col is not None
            and z_type == VariableType.INTERVAL
        )

        cols = [x_col, y_col] + ([z_col] if z_is_line else [])
        sub = df[cols].copy()
        sub[x_col] = self._to_mpl_numeric(sub[x_col], x_type)
        sub[y_col] = pd.to_numeric(sub[y_col], errors='coerce')
        if z_is_line:
            sub[z_col] = pd.to_numeric(sub[z_col], errors='coerce')
        sub = sub.dropna(subset=[x_col, y_col])

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.", ha='center', va='center',
                    transform=ax.transAxes, color="#94A3B8")
            return

        if self._opt("sort_x"):
            sub = sub.sort_values(x_col)

        color   = self._opt("color")   or MPL_ACCENT
        z_color = self._opt("z_color") or "#DC2626"
        marker  = 'o' if self._opt("markers") else None

        if self._opt("conf_band"):
            grouped = sub.groupby(x_col)[y_col]
            means   = grouped.mean()
            sems    = grouped.sem().fillna(0)
            xs = means.index
            ax.plot(xs, means.values, color=color, linewidth=2, marker=marker,
                    markersize=5, label=y_col if z_is_line else None)
            # If most groups have only one observation (typical time series),
            # SEM is 0 everywhere and the band would be invisible.  Fall back
            # to a rolling-window std so the band always shows meaningful spread.
            if (sems == 0).mean() > 0.5:
                window   = max(3, len(means) // 15)
                roll_std = means.rolling(window, center=True, min_periods=1).std(ddof=1).fillna(0)
                lo = (means - 1.96 * roll_std).values
                hi = (means + 1.96 * roll_std).values
            else:
                lo = means.values - 1.96 * sems.values
                hi = means.values + 1.96 * sems.values
            ax.fill_between(xs, lo, hi,
                            color=MPL_CONFIDENCE_BAND, alpha=0.5, label="95% CI")
            ax.legend(fontsize=9, framealpha=0.8)
        else:
            ax.plot(sub[x_col], sub[y_col], color=color, linewidth=2,
                    marker=marker, markersize=5, alpha=0.85,
                    label=y_col if z_is_line else None)

        # ── Second line for Z (trivariate numeric mode) ───────────────────────
        if z_is_line:
            sub_z = sub.dropna(subset=[z_col])
            ax.plot(sub_z[x_col], sub_z[z_col], color=z_color, linewidth=2,
                    marker=marker, markersize=5, alpha=0.85, label=z_col)
            ax.legend(fontsize=9, framealpha=0.8, loc='best')

        if x_type == VariableType.DATE:
            self._apply_date_fmt(ax, 'x', fig)

        x_label = self._opt("x_label") or VariableTransformer.axis_label(x_col, selection.x_transform())
        y_label = self._opt("y_label") or VariableTransformer.axis_label(y_col, selection.y_transform())
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        default_title = (
            f"{y_col} & {z_col} over {x_col}" if z_is_line
            else f"{y_col} over {x_col}"
        )
        self._apply_title(ax, self._opt("title") or default_title)
        self._apply_figure_style(fig, ax)

        # ── Edit dialog visibility ────────────────────────────────────────────
        self._set_visible("z_color", z_is_line)

        fig.tight_layout()
