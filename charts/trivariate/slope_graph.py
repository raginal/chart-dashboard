"""
Slope Graph — shows how a set of entities (Z-axis) changed between two
dates (X-axis) on a numeric measure (Y-axis).

Inspired by Tufte's original slope graphs.  Two vertical "poles" represent
the start and end dates; each entity gets a dot on each pole connected by a
line, with its label to the right of the end-date dot.

Design details
--------------
• By default the earliest and latest dates in the dataset are used as the
  two endpoints.  The user can override both via Quick Edit (accepts any
  string parseable by pandas.to_datetime, e.g. "2005" or "2010-06").

• When an entity has multiple observations on the same date (e.g. monthly
  data pivoted wide), the mean is used.

• A simple iterative nudge algorithm prevents right-side labels from
  overlapping without distorting the line endpoints.

• Date column headers automatically adapt resolution:
    > 1 year apart  → "2000" / "2010"
    > 1 month apart → "Jan 2020" / "Dec 2020"
    otherwise       → "Jan 1, 2020" / "Jan 15, 2020"
"""
from __future__ import annotations
import numpy as np
import pandas as pd
from matplotlib.figure import Figure

from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec
from core.transformer import VariableTransformer
from ui.palette import MPL_ACCENT

# Maximum entities to render (guards against unintelligible hairball)
MAX_ENTITIES = 50


class SlopeGraph(BaseChart):
    CHART_ID       = "slope_graph"
    DISPLAY_NAME   = "Slope Graph"
    DIMENSIONALITY = "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":            {"label": "Title",                   "type": "text", "default": ""},
            "y_label":          {"label": "Y-axis label",             "type": "text", "default": ""},
            "dot_color":        {"label": "Dot colour",               "type": "text", "default": MPL_ACCENT},
            "line_color":       {"label": "Line colour",              "type": "text", "default": "#94A3B8"},
            "dot_size":         {"label": "Dot size (pt)",            "type": "text", "default": "8"},
            "line_width":       {"label": "Line width",               "type": "text", "default": "1.5"},
            "date_start":       {"label": "Start date (override)",    "type": "text", "default": "",
                                 "group": "axes"},
            "date_end":         {"label": "End date (override)",      "type": "text", "default": "",
                                 "group": "axes"},
            "show_left_labels": {"label": "Show left-side values",    "type": "bool", "default": False},
            "gridlines":        {"label": "Show gridlines",           "type": "bool", "default": False},
            "label_size":       {"label": "Label font size",          "type": "text", "default": "9"},
            **BaseChart._title_style_options(),
        }

    # ── Helpers ───────────────────────────────────────────────────────────────

    @staticmethod
    def _fmt_date(dt: pd.Timestamp, span_days: float) -> str:
        """Format a date label with resolution proportional to the time span."""
        if span_days > 365:
            return str(dt.year)
        if span_days > 28:
            return dt.strftime("%b %Y")
        return dt.strftime("%b %-d, %Y")

    @staticmethod
    def _resolve_date(raw: str, available: pd.Series) -> pd.Timestamp | None:
        """
        Parse *raw* (user-supplied string) and return the closest date in
        *available*.  Returns None if *raw* is blank or unparseable.
        """
        raw = (raw or "").strip()
        if not raw:
            return None
        try:
            target = pd.to_datetime(raw)
        except Exception:
            return None
        # Find closest available date by absolute difference
        diffs = (available - target).abs()
        return available.iloc[diffs.argmin()]

    @staticmethod
    def _nudge_labels(
        y_vals: list[float], y_min: float, y_max: float, label_size_pt: float
    ) -> list[float]:
        """
        Iteratively push label y-positions apart so they don't overlap.

        min_gap is derived from label_size_pt converted to the data-unit scale:
        ~1.2× line height as a fraction of the y range.
        """
        n = len(y_vals)
        if n == 0:
            return y_vals

        y_range = max(y_max - y_min, 1e-9)
        # Approximate 1 label height in data units (label_size_pt / 72 inches,
        # mapped through a rough 6-inch axis height).
        min_gap = (label_size_pt * 1.4 / 72.0 / 6.0) * y_range

        # Work on (original_index, value) pairs sorted by value
        indexed = sorted(enumerate(y_vals), key=lambda t: t[1])
        ys = [v for _, v in indexed]

        for _ in range(200):
            moved = False
            for i in range(1, n):
                gap = ys[i] - ys[i - 1]
                if gap < min_gap:
                    mid      = (ys[i] + ys[i - 1]) / 2
                    ys[i - 1] = mid - min_gap / 2
                    ys[i]     = mid + min_gap / 2
                    moved    = True
            if not moved:
                break

        # Map back to original order
        result = [0.0] * n
        for (orig_idx, _), new_y in zip(indexed, ys):
            result[orig_idx] = new_y
        return result

    # ── Render ────────────────────────────────────────────────────────────────

    def render(self, df: pd.DataFrame, selection: VariableSelection, fig: Figure) -> None:
        fig.clear()
        ax = fig.add_subplot(111)

        x_col = selection.x_var
        y_col = selection.y_var
        z_col = selection.group_var

        if z_col is None:
            ax.text(0.5, 0.5, "Select a Z-Axis variable to define entities.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=11)
            return

        # ── Prepare data ──────────────────────────────────────────────────────
        sub = df[[x_col, y_col, z_col]].copy()
        sub[x_col] = pd.to_datetime(sub[x_col], errors="coerce")
        sub[y_col] = pd.to_numeric(sub[y_col],  errors="coerce")
        sub = sub.dropna(subset=[x_col, y_col]).copy()

        if sub.empty:
            ax.text(0.5, 0.5, "No data to display.",
                    ha="center", va="center", transform=ax.transAxes, color="#94A3B8")
            return

        available_dates = sub[x_col].drop_duplicates().sort_values().reset_index(drop=True)

        # ── Resolve start / end dates ─────────────────────────────────────────
        override_start = self._resolve_date(self._opt("date_start") or "", available_dates)
        override_end   = self._resolve_date(self._opt("date_end")   or "", available_dates)

        date_left  = override_start if override_start is not None else available_dates.iloc[0]
        date_right = override_end   if override_end   is not None else available_dates.iloc[-1]

        if date_left == date_right:
            ax.text(0.5, 0.5,
                    "Start and end dates are the same.\n"
                    "Use the date overrides in Quick Edit to pick two different dates.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=10)
            return

        if date_left > date_right:
            date_left, date_right = date_right, date_left

        # ── Aggregate: mean Y per (entity, date) ─────────────────────────────
        pivot = (
            sub[sub[x_col].isin([date_left, date_right])]
            .groupby([z_col, x_col])[y_col]
            .mean()
            .unstack(x_col)
        )

        # Keep only entities that have values at BOTH dates
        pivot = pivot.dropna(subset=[date_left, date_right])

        if pivot.empty:
            ax.text(0.5, 0.5,
                    "No entities have data at both selected dates.\n"
                    "Try different date overrides.",
                    ha="center", va="center", transform=ax.transAxes,
                    color="#94A3B8", fontsize=10)
            return

        if len(pivot) > MAX_ENTITIES:
            pivot = pivot.iloc[:MAX_ENTITIES]

        entities = pivot.index.tolist()
        y_left   = pivot[date_left].tolist()
        y_right  = pivot[date_right].tolist()

        # ── Style options ─────────────────────────────────────────────────────
        dot_color  = self._opt("dot_color")  or MPL_ACCENT
        line_color = self._opt("line_color") or "#94A3B8"
        try:
            dot_size = float(self._opt("dot_size") or 8)
        except (TypeError, ValueError):
            dot_size = 8.0
        try:
            lw = float(self._opt("line_width") or 1.5)
        except (TypeError, ValueError):
            lw = 1.5
        try:
            label_size = float(self._opt("label_size") or 9)
        except (TypeError, ValueError):
            label_size = 9.0
        show_left_labels = bool(self._opt("show_left_labels"))

        # ── Draw lines and dots ───────────────────────────────────────────────
        for yl, yr in zip(y_left, y_right):
            ax.plot([0, 1], [yl, yr], color=line_color, linewidth=lw,
                    solid_capstyle="round", zorder=2)

        ax.scatter([0] * len(y_left),  y_left,  color=dot_color,
                   s=dot_size ** 2, zorder=3, linewidths=0)
        ax.scatter([1] * len(y_right), y_right, color=dot_color,
                   s=dot_size ** 2, zorder=3, linewidths=0)

        # ── Nudge right-side labels ───────────────────────────────────────────
        y_all  = y_left + y_right
        y_min  = min(y_all)
        y_max  = max(y_all)
        nudged = self._nudge_labels(y_right, y_min, y_max, label_size)

        text_x = 1.0 + dot_size * 0.012 + 0.015   # a little right of the dot

        for entity, yr_raw, yr_nudged in zip(entities, y_right, nudged):
            ax.text(text_x, yr_nudged, str(entity),
                    va="center", ha="left", fontsize=label_size,
                    color=self._text_color())

        # ── Optional left-side value annotations ──────────────────────────────
        if show_left_labels:
            nudged_left = self._nudge_labels(y_left, y_min, y_max, label_size)
            left_text_x = 0.0 - dot_size * 0.012 - 0.015
            for yl_raw, yl_nudged in zip(y_left, nudged_left):
                ax.text(left_text_x, yl_nudged,
                        f"{yl_raw:,.4g}",
                        va="center", ha="right", fontsize=label_size,
                        color=self._text_color())

        # ── Column header labels (at top of each pole) ────────────────────────
        span_days = (date_right - date_left).days
        hdr_left  = self._fmt_date(date_left,  span_days)
        hdr_right = self._fmt_date(date_right, span_days)

        ax.set_xticks([0, 1])
        ax.set_xticklabels([hdr_left, hdr_right],
                           fontsize=13, fontweight="bold",
                           color=self._text_color())
        ax.xaxis.set_ticks_position("top")
        ax.xaxis.set_label_position("top")
        ax.tick_params(axis="x", length=0)   # hide tick marks, keep labels

        # ── Y-axis ────────────────────────────────────────────────────────────
        ax.set_xlim(-0.09, text_x + 0.04)    # tight left; modest right margin for labels
        padding = (y_max - y_min) * 0.05 if y_max > y_min else 1
        ax.set_ylim(y_min - padding, y_max + padding)

        ax.yaxis.set_ticks_position("left")
        ax.tick_params(axis="y", labelsize=9, colors=self._text_color())

        # Clean spines — keep left y-axis line only
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["bottom"].set_visible(False)
        ax.spines["left"].set_color(self._spine_color())

        ax.set_facecolor(self._chart_bg())

        y_label = (
            self._opt("y_label")
            or VariableTransformer.axis_label(y_col, selection.y_transform())
        )
        ax.set_ylabel(y_label, color=self._text_color())

        default_title = (
            f"{y_col} — {hdr_left} vs {hdr_right}"
        )
        self._apply_title(ax, self._opt("title") or default_title)
        self._apply_figure_style(fig, ax, grid=bool(self._opt("gridlines")))
        fig.tight_layout()
