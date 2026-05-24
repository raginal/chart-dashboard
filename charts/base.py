"""
Abstract base class for all chart types in chartBuilder.

Every chart module must:
  1. Subclass BaseChart
  2. Set CHART_ID, DISPLAY_NAME, DIMENSIONALITY as class attributes
  3. Implement render(), _default_edit_options(), and get_spec()
  4. Add itself to charts/registry.py

Adding a new chart type requires only creating a new file and one line in registry.py.
"""

from __future__ import annotations
from abc import ABC, abstractmethod
import pandas as pd
import numpy as np
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
from matplotlib.figure import Figure

from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType


class BaseChart(ABC):
    """
    Abstract base for every chart type.

    Edit options schema
    -------------------
    Each key in the dict returned by _default_edit_options() must have the form:
        {
            "label":   str,             # human-readable control label
            "type":    "text"|"bool"|"choice",
            "default": <value>,         # used when no user override exists
            "choices": [...],           # only present for type=="choice"
        }

    The ChartEditDialog reads this schema to auto-build the edit form.
    """

    CHART_ID:       str = ""
    DISPLAY_NAME:   str = ""
    DIMENSIONALITY: str = ""   # "univariate" | "bivariate" | "trivariate"

    def __init__(self):
        self._edit_options: dict = self._default_edit_options()

    # ── Abstract interface ────────────────────────────────────────────────────

    @abstractmethod
    def render(
        self,
        df: pd.DataFrame,
        selection: VariableSelection,
        fig: Figure,
    ) -> None:
        """
        Draw onto the provided Figure.

        Contract
        --------
        - Call fig.clear() at the start of every render.
        - Raise ValueError with a user-readable message on bad data
          (e.g. column not found, wrong type).
        - Do NOT call plt.show(); the canvas widget handles display.
        - Use self._edit_options for user-configurable style choices.
        """

    @abstractmethod
    def _default_edit_options(self) -> dict:
        """
        Return a dict describing all editable options for this chart.
        Called once in __init__; user edits are stored in self._edit_options.
        """

    @classmethod
    @abstractmethod
    def get_spec(cls) -> ChartSpec:
        """Return a ChartSpec describing this chart (used by ChartSelector)."""

    # ── Edit option management ────────────────────────────────────────────────

    def update_edit_options(self, opts: dict) -> None:
        """Merge user-supplied option values into the stored options."""
        for key, schema in self._edit_options.items():
            if key in opts:
                schema["value"] = opts[key]

    def get_edit_options(self) -> dict:
        """Return a copy of the current edit options (including user values)."""
        return {
            key: dict(schema)
            for key, schema in self._edit_options.items()
        }

    def _opt(self, key: str):
        """Convenience: return the current value for an edit option."""
        schema = self._edit_options.get(key, {})
        return schema.get("value", schema.get("default"))

    # ── Shared rendering helpers ──────────────────────────────────────────────

    @staticmethod
    def _apply_figure_style(fig: Figure, ax) -> None:
        """Apply consistent styling: spine colour, grid, font."""
        ax.spines["top"].set_visible(False)
        ax.spines["right"].set_visible(False)
        ax.spines["left"].set_color("#CBD5E1")
        ax.spines["bottom"].set_color("#CBD5E1")
        ax.tick_params(colors="#334155", labelsize=10)
        ax.xaxis.label.set_color("#334155")
        ax.yaxis.label.set_color("#334155")
        ax.title.set_color("#0F172A")
        ax.grid(axis="y", color="#E2E8F0", linewidth=0.8, zorder=0)
        fig.patch.set_facecolor("white")
        ax.set_facecolor("white")

    @staticmethod
    def _large_data_sample(df: pd.DataFrame, limit: int = 50_000) -> tuple[pd.DataFrame, bool]:
        """
        If df has more than `limit` rows, return a random sample and True.
        Otherwise return (df, False).
        """
        if len(df) > limit:
            return df.sample(limit, random_state=42), True
        return df, False

    # ── Date-handling helpers ─────────────────────────────────────────────────

    @staticmethod
    def _to_mpl_numeric(series: pd.Series, vtype=None) -> pd.Series:
        """
        Convert a series to plottable float values.

        • DATE columns → matplotlib date numbers (float days since epoch).
          This lets every matplotlib plot type (hist, scatter, hexbin, …)
          render date values correctly once the axis formatter is also set.
        • All other columns → pd.to_numeric(errors='coerce').
        """
        if vtype == VariableType.DATE:
            dt = pd.to_datetime(series, errors='coerce')
            # mdates.date2num handles NaT → NaN automatically
            nums = mdates.date2num(dt)
            return pd.Series(nums, index=series.index, dtype=float)
        return pd.to_numeric(series, errors='coerce')

    @staticmethod
    def _apply_date_fmt(ax, which: str = 'x', fig=None) -> None:
        """
        Apply AutoDateFormatter to one axis of *ax*.

        Parameters
        ----------
        ax    : matplotlib Axes
        which : 'x' or 'y'
        fig   : optional Figure — when provided and which=='x',
                ``fig.autofmt_xdate()`` is also called for nice rotation.
        """
        loc = mdates.AutoDateLocator()
        fmt = mdates.AutoDateFormatter(loc)
        if which == 'x':
            ax.xaxis.set_major_locator(loc)
            ax.xaxis.set_major_formatter(fmt)
            if fig is not None:
                fig.autofmt_xdate(rotation=30, ha='right')
        else:
            ax.yaxis.set_major_locator(loc)
            ax.yaxis.set_major_formatter(fmt)

    @staticmethod
    def _add_sample_note(ax, n_sampled: int) -> None:
        """Add a small annotation noting that data was sampled."""
        ax.annotate(
            f"Showing a random sample of {n_sampled:,} rows",
            xy=(0.99, 0.01),
            xycoords="axes fraction",
            ha="right", va="bottom",
            fontsize=8,
            color="#94A3B8",
        )

    # ── Title style helpers ───────────────────────────────────────────────────

    @staticmethod
    def _title_style_options() -> dict:
        """
        Shared edit-option schema entries for title bold and alignment.

        Merge these into every chart's _default_edit_options() with:
            **BaseChart._title_style_options()
        """
        return {
            "title_bold":  {"label": "Bold title",      "type": "bool",   "default": True},
            "title_align": {"label": "Title alignment", "type": "choice", "default": "Center",
                            "choices": ["Center", "Left", "Right"]},
        }

    def _apply_title(self, ax, title_text: str, *,
                     fontsize: int = 13, pad: int = 10) -> None:
        """
        Set the axes title, honouring the 'title_bold' and 'title_align'
        edit options.  Replaces direct ax.set_title() calls in render().
        """
        bold = self._opt("title_bold")
        bold = True if bold is None else bool(bold)
        align_str = self._opt("title_align") or "Center"
        loc = {"Center": "center", "Left": "left", "Right": "right"}.get(
            align_str, "center"
        )
        ax.set_title(
            title_text,
            fontsize=fontsize,
            fontweight="bold" if bold else "normal",
            pad=pad,
            loc=loc,
        )

    def _apply_suptitle(self, fig, title_text: str, *,
                        fontsize: int = 12, y: float = 0.98) -> None:
        """
        Set the figure suptitle (used by multi-panel charts), honouring the
        'title_bold' and 'title_align' edit options.
        """
        bold = self._opt("title_bold")
        bold = True if bold is None else bool(bold)
        align_str = self._opt("title_align") or "Center"
        x_pos = {"Center": 0.5,  "Left": 0.05, "Right": 0.95}.get(align_str, 0.5)
        ha    = {"Center": "center", "Left": "left", "Right": "right"}.get(
            align_str, "center"
        )
        fig.suptitle(
            title_text,
            fontsize=fontsize,
            fontweight="bold" if bold else "normal",
            y=y,
            x=x_pos,
            ha=ha,
        )
