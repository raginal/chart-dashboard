"""
Range Line Plot — seasonal context chart for Date × Numeric pairs.

Inspired by EIA-style inventory ribbon charts.  The chart splits the data into
two calendar-aligned periods:

• **Historical period** — grouped by calendar position to build a min–max
  ribbon (and optional average line).

• **Current period** — the current calendar year, plotted as a long-dashed
  line over the same x-axis.

The x-axis always spans the **full current calendar year** (Jan 1 – Dec 31),
even when the data has not yet reached year-end, so you always see the
complete annual window.

Range modes
-----------
  "1 Year"   — current year vs 1 prior year of history.
  "5 Years"  — current year vs 5 prior calendar years.  (default)
  "10 Years" — current year vs 10 prior calendar years.

Calendar grouping is **inferred from the data cadence**:
  daily    → day-of-year   (up to 366 positions)
  weekly   → ISO week      (1–53)
  monthly  → month number  (1–12)
  quarterly→ quarter       (1–4)

X-axis tick labels are formatted to match that cadence so the chart always
reads intuitively regardless of whether the underlying data is weekly EIA
inventory, monthly economic releases, or quarterly earnings.
"""
from __future__ import annotations
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

    # ── Data-frequency detection ──────────────────────────────────────────────

    @staticmethod
    def _detect_freq(sorted_dates: pd.Series) -> str:
        """
        Infer cadence from a sorted datetime Series.
        Returns one of: 'daily' | 'weekly' | 'monthly' | 'quarterly'.
        """
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
    def _calendar_key(dates: pd.Series, data_freq: str) -> pd.Series:
        """Map a datetime Series to integer calendar-position keys."""
        if data_freq == "daily":
            return dates.dt.dayofyear
        if data_freq == "weekly":
            return dates.dt.isocalendar().week.astype(int)
        if data_freq == "monthly":
            return dates.dt.month
        # quarterly
        return dates.dt.quarter

    # ── Ribbon projection frequency ───────────────────────────────────────────

    _RIBBON_FREQ: dict[str, str] = {
        "daily":     "D",
        "weekly":    "7D",
        "monthly":   "MS",
        "quarterly": "QS",
    }

    # ── Period boundaries ─────────────────────────────────────────────────────

    @staticmethod
    def _period_boundaries(
        end: pd.Timestamp, period: str
    ) -> tuple[pd.Timestamp, pd.Timestamp, pd.Timestamp]:
        """
        Return (current_start, hist_start, x_axis_end).

        All three periods share the same structure — only the number of
        historical years differs.  The current period is always the current
        calendar year; the x-axis always extends to Dec 31 of that year.
        """
        n_hist = {"1 Year": 1, "5 Years": 5, "10 Years": 10}.get(period, 5)
        yr            = end.year
        current_start = pd.Timestamp(yr, 1, 1)
        hist_start    = pd.Timestamp(yr - n_hist, 1, 1)
        x_axis_end    = pd.Timestamp(yr, 12, 31)
        return current_start, hist_start, x_axis_end

    # ── Axis formatting ───────────────────────────────────────────────────────

    @staticmethod
    def _apply_range_axis_fmt(ax, data_freq: str, fig: Figure) -> None:
        """
        Set x-axis tick locator + formatter to match the data cadence.

        daily / weekly  → monthly major ticks, abbreviated month label
        monthly         → monthly major ticks, abbreviated month label
        quarterly       → quarterly major ticks, "Q1 / Q2 / …" labels
        """
        if data_freq in ("daily", "weekly", "monthly"):
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

        # ── Detect data frequency from the full series ────────────────────────
        data_freq = self._detect_freq(sub[x_col])

        # ── Calendar-aligned period split ─────────────────────────────────────
        period = self._opt("period") or "5 Years"
        end_date      = sub[x_col].max()
        current_start, hist_start, x_axis_end = self._period_boundaries(end_date, period)

        current    = sub[sub[x_col] >= current_start].copy()
        historical = sub[
            (sub[x_col] >= hist_start) & (sub[x_col] < current_start)
        ].copy()

        if current.empty:
            ax.text(0.5, 0.5,
                    "Not enough data for the current year.\n"
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
        hist_keys  = self._calendar_key(historical[x_col], data_freq)
        hist_stats = (
            historical.assign(_key=hist_keys)
            .groupby("_key")[y_col]
            .agg(["min", "max", "mean"])
        )

        # ── Project ribbon across the FULL current year ───────────────────────
        # Generate a date range at the natural data cadence.  Then append
        # x_axis_end (Dec 31) as a closing sentinel if the last natural date
        # falls short.  The sentinel forward-fills the last period's calendar
        # key so the ribbon extends to Dec 31 without any gap:
        #   e.g. quarterly: Oct 1 → Dec 31 filled with Q4 min/max
        #         monthly:  Dec 1 → Dec 31 filled with December min/max
        ribbon_dates = pd.date_range(
            current_start, x_axis_end, freq=self._RIBBON_FREQ[data_freq]
        )
        if len(ribbon_dates) == 0 or ribbon_dates[-1] < x_axis_end - pd.Timedelta(days=1):
            ribbon_dates = ribbon_dates.append(pd.DatetimeIndex([x_axis_end]))

        ribbon_keys_s = self._calendar_key(pd.Series(ribbon_dates), data_freq).copy()
        # Forward-fill the sentinel point so it inherits the last real period's key
        if len(ribbon_keys_s) > 1 and ribbon_dates[-1] == x_axis_end:
            ribbon_keys_s.iloc[-1] = ribbon_keys_s.iloc[-2]

        band_min    = ribbon_keys_s.map(hist_stats["min"]).values.astype(float)
        band_max    = ribbon_keys_s.map(hist_stats["max"]).values.astype(float)
        band_mean   = ribbon_keys_s.map(hist_stats["mean"]).values.astype(float)
        ribbon_x    = ribbon_dates.values   # numpy datetime64 — matplotlib handles natively

        # ── Draw range ribbon ─────────────────────────────────────────────────
        range_color   = self._opt("range_color")   or "#CBD5E1"
        current_color = self._opt("current_color") or MPL_ACCENT
        period_label  = self._PERIOD_LABELS.get(period, "Range")

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
                    label=f"{period_label} Avg",
                    zorder=3,
                )

        # ── Current-year line (long-dashed, actual data only) ─────────────────
        ax.plot(
            current[x_col].values,
            current[y_col].values,
            color=current_color,
            linewidth=2,
            linestyle=(0, (8, 4)),   # long-dash pattern
            label="Current Year",
            zorder=4,
        )

        # ── Force x-axis to span the full current year ───────────────────────
        ax.set_xlim(pd.Timestamp(current_start), pd.Timestamp(x_axis_end))

        # ── Data-cadence-aware axis labels ────────────────────────────────────
        self._apply_range_axis_fmt(ax, data_freq, fig)

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
