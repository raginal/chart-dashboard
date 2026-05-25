"""
Range Line Plot — seasonal context chart for Date × Numeric pairs.

Inspired by EIA-style inventory ribbon charts.  The chart splits the data into
two periods using **calendar-aligned** boundaries:

• **Historical period** — grouped by calendar position to compute a
  min–max ribbon and an optional average line.

• **Current period** — the most-recent slice, plotted as a long-dashed
  line over the same x-axis.

The x-axis always extends to the **end of the current period unit**, even
if data has not yet reached that date, so you always see the full year/
month window.

Range modes
-----------
  "5 Years"  (default) — current = current calendar year;
                          historical = 5 prior calendar years.
                          Calendar key = ISO week-of-year.
                          X-axis: Jan 1 – Dec 31 of current year.

  "10 Years"           — same structure, 10 prior calendar years.

  "1 Year"             — current = current calendar month;
                          historical = 12 prior calendar months.
                          Calendar key = day-of-month.
                          X-axis: 1st – last day of current month.

  "1 Month"            — current = current calendar month;
                          historical = 3 prior calendar months
                          (giving ≥ 3 values per day-of-month for a
                          meaningful ribbon).
                          Calendar key = day-of-month.
                          X-axis: 1st – last day of current month.
"""
from __future__ import annotations
import calendar as _cal
import numpy as np
import pandas as pd
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
        "1 Month":  "3-mo Range",
    }
    _CURRENT_LABELS: dict[str, str] = {
        "5 Years":  "Current Year",
        "10 Years": "Current Year",
        "1 Year":   "Current Month",
        "1 Month":  "Current Month",
    }

    def _period_boundaries(
        self, end: pd.Timestamp, period: str
    ) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp, str]:
        """
        Return (current_start, hist_start, x_axis_end, group_key).

        All boundaries are **calendar-aligned** so the x-axis always
        represents a complete period unit (full year or full month).

        group_key: "weekofyear" | "dayofmonth"
        """
        if period in ("5 Years", "10 Years"):
            n             = 5 if period == "5 Years" else 10
            yr            = end.year
            current_start = pd.Timestamp(yr, 1, 1)
            hist_start    = pd.Timestamp(yr - n, 1, 1)
            x_axis_end    = pd.Timestamp(yr, 12, 31)
            return current_start, hist_start, x_axis_end, "weekofyear"

        # "1 Year" and "1 Month" — calendar-month unit
        yr, mo        = end.year, end.month
        current_start = pd.Timestamp(yr, mo, 1)
        last_day      = _cal.monthrange(yr, mo)[1]
        x_axis_end    = pd.Timestamp(yr, mo, last_day)

        if period == "1 Year":
            hist_start = current_start - pd.DateOffset(years=1)
        else:  # "1 Month" — use 3 prior months for a real min-max spread
            hist_start = current_start - pd.DateOffset(months=3)

        return current_start, hist_start, x_axis_end, "dayofmonth"

    @staticmethod
    def _calendar_key(dates: pd.Series, group_key: str) -> pd.Series:
        """Map a datetime Series to integer calendar-position keys."""
        if group_key == "weekofyear":
            return dates.dt.isocalendar().week.astype(int)
        # "dayofmonth"
        return dates.dt.day

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

        # ── Calendar-aligned period split ─────────────────────────────────────
        period = self._opt("period") or "5 Years"
        end_date = sub[x_col].max()
        current_start, hist_start, x_axis_end, group_key = self._period_boundaries(
            end_date, period
        )

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
        hist_keys  = self._calendar_key(historical[x_col], group_key)
        hist_stats = (
            historical.assign(_key=hist_keys)
            .groupby("_key")[y_col]
            .agg(["min", "max", "mean"])
        )

        # ── Build a full-period date range for the ribbon ─────────────────────
        # This extends the ribbon across the ENTIRE current period unit (e.g.
        # all 52 weeks of the year) even where current-period data doesn't
        # exist yet.
        ribbon_freq   = "7D" if group_key == "weekofyear" else "D"
        ribbon_dates  = pd.date_range(current_start, x_axis_end, freq=ribbon_freq)
        ribbon_keys   = self._calendar_key(pd.Series(ribbon_dates), group_key)
        band_min      = ribbon_keys.map(hist_stats["min"]).values.astype(float)
        band_max      = ribbon_keys.map(hist_stats["max"]).values.astype(float)
        band_mean     = ribbon_keys.map(hist_stats["mean"]).values.astype(float)
        ribbon_x      = ribbon_dates.values   # numpy datetime64

        # ── Draw range ribbon ─────────────────────────────────────────────────
        range_color   = self._opt("range_color")   or "#CBD5E1"
        current_color = self._opt("current_color") or MPL_ACCENT
        period_label  = self._PERIOD_LABELS.get(period, "Range")
        current_label = self._CURRENT_LABELS.get(period, "Current")

        valid = ~(np.isnan(band_min) | np.isnan(band_max))
        if valid.any():
            ax.fill_between(
                ribbon_x,
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
                    ribbon_x,
                    np.where(valid_mean, band_mean, np.nan),
                    color="#64748B",
                    linewidth=1.4,
                    linestyle="-",
                    label=f"{period_label} Average",
                    zorder=3,
                )

        # ── Current period line (long-dashed, actual data only) ───────────────
        ax.plot(
            current[x_col].values,
            current[y_col].values,
            color=current_color,
            linewidth=2,
            linestyle=(0, (8, 4)),   # long-dash pattern
            label=current_label,
            zorder=4,
        )

        # ── Force x-axis to span the full current period unit ─────────────────
        ax.set_xlim(pd.Timestamp(current_start), pd.Timestamp(x_axis_end))

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
