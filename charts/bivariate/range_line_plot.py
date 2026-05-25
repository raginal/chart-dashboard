"""
Range Line Plot — seasonal context chart for Date × Numeric pairs.

Inspired by EIA-style inventory ribbon charts.  The chart splits the data
into two calendar-aligned periods:

• **Historical period** — grouped by calendar position to build a min–max
  ribbon and optional average line.

• **Current period** — plotted as a line (dashed or solid) over the same
  x-axis.

Range modes
-----------
  "1 Year"   — current calendar MONTH vs the 12 prior calendar months.
               X-axis spans day 1 → last day of the current month.
               Group key adapts to cadence:
                 weekly → week-of-month (1–5)
                 daily  → day-of-month  (1–31)
               Legend: "1-yr Range" / "Current Month"

  "5 Years"  — current calendar YEAR vs 5 prior calendar years. (default)
  "10 Years" — current calendar YEAR vs 10 prior calendar years.
               Both use the annual view: x-axis Jan 1 → Dec 31.
               Group key adapts to cadence:
                 daily     → day-of-year (366 positions)
                 weekly    → ISO week    (1–53)
                 monthly   → month       (1–12)
                 quarterly → quarter     (1–4)
               Legend: "N-yr Range" / "Current Year"

X-axis ticks are formatted to match cadence:
  daily/weekly/monthly → abbreviated month names  (Jan … Dec)
  quarterly            → quarter labels           (Q1 Q2 Q3 Q4)
  1-Year monthly view  → day-of-month labels      (1  8  15  22  29)
"""
from __future__ import annotations
import calendar as _cal
import numpy as np
import pandas as pd
from matplotlib.figure import Figure
from matplotlib.ticker import FuncFormatter
import matplotlib.dates as mdates

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
            "title":         {"label": "Title",                "type": "text",   "default": ""},
            "x_label":       {"label": "X-axis label",          "type": "text",   "default": ""},
            "y_label":       {"label": "Y-axis label",          "type": "text",   "default": ""},
            "period":        {"label": "Range period",          "type": "choice", "default": "5 Years",
                              "choices": ["1 Year", "5 Years", "10 Years"]},
            "line_style":    {"label": "Current period line",   "type": "choice", "default": "Dashed",
                              "choices": ["Dashed", "Solid"],   "group": "other"},
            "markers":       {"label": "Show data markers",     "type": "bool",   "default": False},
            "show_mean":     {"label": "Show range average",    "type": "bool",   "default": False},
            "current_color": {"label": "Current period colour", "type": "text",   "default": MPL_ACCENT},
            "range_color":   {"label": "Range colour",          "type": "text",   "default": "#CBD5E1"},
            **BaseChart._title_style_options(),
        }

    # ── Period labels ─────────────────────────────────────────────────────────

    _PERIOD_LABELS: dict[str, str] = {
        "1 Year":   "1-yr Range",
        "5 Years":  "5-yr Range",
        "10 Years": "10-yr Range",
    }
    _CURRENT_LABELS: dict[str, str] = {
        "1 Year":   "Current Month",
        "5 Years":  "Current Year",
        "10 Years": "Current Year",
    }

    # ── Data-frequency detection ──────────────────────────────────────────────

    @staticmethod
    def _detect_freq(sorted_dates: pd.Series) -> str:
        """Infer cadence: 'daily' | 'weekly' | 'monthly' | 'quarterly'."""
        if len(sorted_dates) < 2:
            return "weekly"
        gaps = sorted_dates.diff().dropna().dt.days
        med  = gaps.median()
        if med < 3:
            return "daily"
        if med < 10:
            return "weekly"
        if med < 45:
            return "monthly"
        return "quarterly"

    # ── Calendar-key helpers ──────────────────────────────────────────────────

    @staticmethod
    def _calendar_key(dates: pd.Series, group_key: str) -> pd.Series:
        """Map a datetime Series to integer calendar-position keys."""
        if group_key == "dayofyear":
            return dates.dt.dayofyear
        if group_key == "weekofyear":
            return dates.dt.isocalendar().week.astype(int)
        if group_key == "month":
            return dates.dt.month
        if group_key == "quarter":
            return dates.dt.quarter
        if group_key == "dayofmonth":
            return dates.dt.day
        if group_key == "weekofmonth":
            # 1 = days 1–7, 2 = days 8–14, 3 = days 15–21, 4 = days 22–28, 5 = days 29–31
            return (dates.dt.day - 1) // 7 + 1
        return dates.dt.day   # fallback

    @staticmethod
    def _freq_to_group_key(data_freq: str) -> str:
        """Map a cadence string to the annual-view group key."""
        return {
            "daily":     "dayofyear",
            "weekly":    "weekofyear",
            "monthly":   "month",
            "quarterly": "quarter",
        }.get(data_freq, "weekofyear")

    # ── Ribbon projection frequency ───────────────────────────────────────────

    _RIBBON_FREQ: dict[str, str] = {
        "daily":     "D",
        "weekly":    "7D",
        "monthly":   "MS",
        "quarterly": "QS",
    }

    # ── Axis formatting ───────────────────────────────────────────────────────

    @staticmethod
    def _apply_range_axis_fmt(
        ax, view: str, data_freq: str, fig: Figure
    ) -> None:
        """
        Set x-axis tick locator + formatter.

        view == 'monthly'  (1 Year):  weekly ticks, day-of-month labels
        view == 'annual'   (5Y/10Y):  monthly or quarterly ticks
        """
        if view == "monthly":
            ax.xaxis.set_major_locator(mdates.DayLocator(interval=7))
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%-d"))
            fig.autofmt_xdate(rotation=0, ha="center")
        elif data_freq in ("daily", "weekly", "monthly"):
            ax.xaxis.set_major_locator(mdates.MonthLocator())
            ax.xaxis.set_major_formatter(mdates.DateFormatter("%b"))
            fig.autofmt_xdate(rotation=30, ha="right")
        else:  # quarterly
            ax.xaxis.set_major_locator(mdates.MonthLocator(bymonth=[1, 4, 7, 10]))

            def _qfmt(x, _pos):
                dt = mdates.num2date(x)
                return f"Q{(dt.month - 1) // 3 + 1}"

            ax.xaxis.set_major_formatter(FuncFormatter(_qfmt))
            fig.autofmt_xdate(rotation=0, ha="center")

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var

        # ── Clean data ────────────────────────────────────────────────────────
        sub = df[[x_col, y_col]].copy()
        sub[x_col] = pd.to_datetime(sub[x_col], errors="coerce")
        sub[y_col] = pd.to_numeric(sub[y_col],  errors="coerce")
        sub = sub.dropna().sort_values(x_col).reset_index(drop=True)

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        data_freq = self._detect_freq(sub[x_col])
        period    = self._opt("period") or "5 Years"
        end_date  = sub[x_col].max()

        # ── Period boundaries and group key ───────────────────────────────────
        if period == "1 Year":
            # Monthly view: current calendar month vs 12 prior months
            yr, mo        = end_date.year, end_date.month
            current_start = pd.Timestamp(yr, mo, 1)
            hist_start    = current_start - pd.DateOffset(years=1)
            last_day      = _cal.monthrange(yr, mo)[1]
            x_axis_end    = pd.Timestamp(yr, mo, last_day)
            group_key     = "weekofmonth" if data_freq == "weekly" else "dayofmonth"
            ribbon_freq   = "D"           # daily ribbon for smooth monthly fill
            view          = "monthly"
        else:
            # Annual view: current calendar year vs N prior years
            n             = 5 if period == "5 Years" else 10
            yr            = end_date.year
            current_start = pd.Timestamp(yr, 1, 1)
            hist_start    = pd.Timestamp(yr - n, 1, 1)
            x_axis_end    = pd.Timestamp(yr, 12, 31)
            group_key     = self._freq_to_group_key(data_freq)
            ribbon_freq   = self._RIBBON_FREQ[data_freq]
            view          = "annual"

        # ── Split into current and historical ─────────────────────────────────
        current    = sub[sub[x_col] >= current_start].copy()
        historical = sub[
            (sub[x_col] >= hist_start) & (sub[x_col] < current_start)
        ].copy()

        if current.empty:
            label = "month" if view == "monthly" else "year"
            ax.text(0.5, 0.5,
                    f"Not enough data for the current {label}.\n"
                    "Try a shorter range period.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=10)
            return

        if historical.empty:
            ax.text(0.5, 0.5,
                    "Not enough historical data to compute the range.\n"
                    "Try a shorter range period or load a longer dataset.",
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

        # ── Project ribbon across the full period ─────────────────────────────
        # Generate ribbon dates at the chosen frequency, then append x_axis_end
        # as a closing sentinel so the last period (e.g. Q4, Dec, last week)
        # fills all the way to the axis edge.
        ribbon_dates = pd.date_range(current_start, x_axis_end, freq=ribbon_freq)
        if len(ribbon_dates) == 0 or ribbon_dates[-1] < x_axis_end - pd.Timedelta(days=1):
            ribbon_dates = ribbon_dates.append(pd.DatetimeIndex([x_axis_end]))

        ribbon_keys_s = self._calendar_key(pd.Series(ribbon_dates), group_key).copy()
        # Forward-fill sentinel point so it inherits the last real period's key
        if len(ribbon_keys_s) > 1 and ribbon_dates[-1] == x_axis_end:
            ribbon_keys_s.iloc[-1] = ribbon_keys_s.iloc[-2]

        band_min  = ribbon_keys_s.map(hist_stats["min"]).values.astype(float)
        band_max  = ribbon_keys_s.map(hist_stats["max"]).values.astype(float)
        band_mean = ribbon_keys_s.map(hist_stats["mean"]).values.astype(float)
        ribbon_x  = ribbon_dates.values

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
                alpha=0.45, color=range_color, label=period_label, zorder=2,
            )

        # ── Optional range average ────────────────────────────────────────────
        if self._opt("show_mean"):
            valid_mean = ~np.isnan(band_mean)
            if valid_mean.any():
                ax.plot(
                    ribbon_x,
                    np.where(valid_mean, band_mean, np.nan),
                    color="#64748B", linewidth=1.4, linestyle="-",
                    label=f"{period_label} Avg", zorder=3,
                )

        # ── Current-period line ───────────────────────────────────────────────
        ls     = "-" if (self._opt("line_style") or "Dashed") == "Solid" else (0, (8, 4))
        marker = "o" if self._opt("markers") else None
        ax.plot(
            current[x_col].values,
            current[y_col].values,
            color=current_color, linewidth=2, linestyle=ls,
            marker=marker, markersize=4, markerfacecolor=current_color,
            label=current_label, zorder=4,
        )

        # ── X-axis limits ─────────────────────────────────────────────────────
        if view == "monthly":
            # Day 1 flush with y-axis; last day + 2-day right margin
            ax.set_xlim(current_start, x_axis_end + pd.Timedelta(days=2))
        else:
            # Annual: Jan 1 flush left; half-interval right margin after last tick
            if data_freq == "quarterly":
                last_tick    = pd.Timestamp(yr, 10, 1)
                right_margin = pd.Timedelta(days=46)
            else:
                last_tick    = pd.Timestamp(yr, 12, 1)
                right_margin = pd.Timedelta(days=16)
            ax.set_xlim(pd.Timestamp(yr, 1, 1), last_tick + right_margin)

        # ── Cadence-aware tick labels ─────────────────────────────────────────
        self._apply_range_axis_fmt(ax, view, data_freq, fig)

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
