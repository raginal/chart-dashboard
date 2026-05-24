"""
Range Line Plot — seasonal context chart for Date × Numeric pairs.

Inspired by EIA-style inventory ribbon charts.  The chart splits the data into
two periods:

• **Historical period** (non-current) — grouped by calendar position
  (week-of-year, day-of-year, or day-of-month depending on the chosen range
  mode) to compute a min–max ribbon and an optional average line.

• **Current period** — the most-recent slice of the data, plotted as a
  long-dashed line over the same x-axis (actual dates).

Range modes
-----------
  "5 Years"  (default) — current = last 365 days; historical = 4 prior years.
                         Calendar key = ISO week-of-year.
  "10 Years"           — current = last 365 days; historical = 9 prior years.
                         Calendar key = ISO week-of-year.
  "1 Year"             — current = last 31 days; historical = prior 11 months.
                         Calendar key = day-of-year.
  "1 Month"            — current = last 1 day;  historical = prior 30 days.
                         Calendar key = day-of-month.

The x-axis always shows **actual dates** for the current period; the range
ribbon is projected onto those dates using their calendar key.
"""
from __future__ import annotations
import pandas as pd
import numpy as np
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT


class RangeLinePlot(BaseChart):
    CHART_ID       = "range_line_plot"
    DISPLAY_NAME   = "Range Line Plot"
    DIMENSIONALITY = "bivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":         {"label": "Title",               "type": "text",   "default": ""},
            "x_label":       {"label": "X-axis label",         "type": "text",   "default": ""},
            "y_label":       {"label": "Y-axis label",         "type": "text",   "default": ""},
            "period":        {"label": "Range period",         "type": "choice", "default": "5 Years",
                              "choices": ["5 Years", "10 Years", "1 Year", "1 Month"]},
            "show_mean":     {"label": "Show range average",   "type": "bool",   "default": False},
            "current_color": {"label": "Current period colour","type": "text",   "default": MPL_ACCENT},
            "range_color":   {"label": "Range colour",         "type": "text",   "default": "#CBD5E1"},
            **BaseChart._title_style_options(),
        }

    # ── Period / label helpers ────────────────────────────────────────────────

    _PERIOD_LABELS: dict[str, str] = {
        "5 Years":  "5-yr Range",
        "10 Years": "10-yr Range",
        "1 Year":   "1-yr Range",
        "1 Month":  "1-mo Range",
    }
    _CURRENT_LABELS: dict[str, str] = {
        "5 Years":  "Current Year",
        "10 Years": "Current Year",
        "1 Year":   "Current Month",
        "1 Month":  "Current Day",
    }

    def _period_boundaries(
        self, end: "pd.Timestamp", period: str
    ) -> tuple["pd.Timestamp", "pd.Timestamp", str]:
        """
        Return (current_start, hist_start, group_key) for the chosen period.

        group_key is one of: "weekofyear" | "dayofyear" | "day"
        """
        if period == "5 Years":
            return (
                end - pd.DateOffset(years=1),
                end - pd.DateOffset(years=5),
                "weekofyear",
            )
        if period == "10 Years":
            return (
                end - pd.DateOffset(years=1),
                end - pd.DateOffset(years=10),
                "weekofyear",
            )
        if period == "1 Year":
            return (
                end - pd.DateOffset(days=31),
                end - pd.DateOffset(years=1),
                "dayofyear",
            )
        # "1 Month"
        return (
            end - pd.DateOffset(days=1),
            end - pd.DateOffset(months=1),
            "day",
        )

    @staticmethod
    def _calendar_key(dates: "pd.Series", group_key: str) -> "pd.Series":
        """Map a datetime Series to integer calendar-position keys."""
        if group_key == "weekofyear":
            return dates.dt.isocalendar().week.astype(int)
        if group_key == "dayofyear":
            return dates.dt.dayofyear
        return dates.dt.day  # day-of-month

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var

        # ── Clean data ────────────────────────────────────────────────────────
        sub = df[[x_col, y_col]].copy()
        sub[x_col] = pd.to_datetime(sub[x_col], errors="coerce")
        sub[y_col] = pd.to_numeric(sub[y_col], errors="coerce")
        sub = sub.dropna().sort_values(x_col).reset_index(drop=True)

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        # ── Period split ──────────────────────────────────────────────────────
        period = self._opt("period") or "5 Years"
        end_date = sub[x_col].max()
        current_start, hist_start, group_key = self._period_boundaries(end_date, period)

        current    = sub[sub[x_col] >= current_start].copy()
        historical = sub[
            (sub[x_col] >= hist_start) & (sub[x_col] < current_start)
        ].copy()

        if current.empty:
            ax.text(0.5, 0.5,
                    "Not enough data for the current period.\n"
                    "Try a shorter range period.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=10)
            return

        if historical.empty:
            ax.text(0.5, 0.5,
                    "Not enough historical data to compute the range.\n"
                    "Try a longer range period or a dataset with more history.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=10)
            return

        # ── Aggregate historical by calendar position ─────────────────────────
        hist_keys = self._calendar_key(historical[x_col], group_key)
        hist_stats = (
            historical.assign(_key=hist_keys)
            .groupby("_key")[y_col]
            .agg(["min", "max", "mean"])
        )

        # ── Map ribbon to current dates ───────────────────────────────────────
        cur_keys  = self._calendar_key(current[x_col], group_key)
        band_min  = cur_keys.map(hist_stats["min"]).values
        band_max  = cur_keys.map(hist_stats["max"]).values
        band_mean = cur_keys.map(hist_stats["mean"]).values
        x_dates   = current[x_col].values   # numpy datetime64 — matplotlib handles natively
        y_vals    = current[y_col].values

        # ── Draw range ribbon ─────────────────────────────────────────────────
        range_color   = self._opt("range_color")   or "#CBD5E1"
        current_color = self._opt("current_color") or MPL_ACCENT
        period_label  = self._PERIOD_LABELS.get(period, "Range")
        current_label = self._CURRENT_LABELS.get(period, "Current")

        valid = ~(np.isnan(band_min) | np.isnan(band_max))
        if valid.any():
            ax.fill_between(
                x_dates,
                np.where(valid, band_min, np.nan),
                np.where(valid, band_max, np.nan),
                alpha=0.45,
                color=range_color,
                label=period_label,
                zorder=2,
            )

        # ── Optional range average ────────────────────────────────────────────
        if self._opt("show_mean"):
            valid_mean = ~np.isnan(band_mean)
            if valid_mean.any():
                ax.plot(
                    x_dates,
                    np.where(valid_mean, band_mean, np.nan),
                    color="#64748B",
                    linewidth=1.4,
                    linestyle="-",
                    label=f"{period_label} Average",
                    zorder=3,
                )

        # ── Current period line (long-dashed) ─────────────────────────────────
        ax.plot(
            x_dates,
            y_vals,
            color=current_color,
            linewidth=2,
            linestyle=(0, (8, 4)),   # long-dash pattern
            label=current_label,
            zorder=4,
        )

        # ── Date axis, legend, labels ─────────────────────────────────────────
        self._apply_date_fmt(ax, "x", fig)
        ax.legend(fontsize=9, framealpha=0.85, loc="best")

        x_label = (
            self._opt("x_label")
            or VariableTransformer.axis_label(x_col, selection.x_transform())
        )
        y_label = (
            self._opt("y_label")
            or VariableTransformer.axis_label(y_col, selection.y_transform())
        )
        ax.set_xlabel(x_label)
        ax.set_ylabel(y_label)

        self._apply_title(
            ax,
            self._opt("title") or f"{y_col} — {period} Range",
        )
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
