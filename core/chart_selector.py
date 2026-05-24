"""
Chart applicability logic.

Given a VariableSelection, determines which charts from the registry
are applicable.  This is pure business logic — no GUI imports.

Variable slots
--------------
  x_var     — X-Axis (required for any chart)
  y_var     — Y-Axis
  group_var — Z-Axis (replaces former Group By / Colour By / 2nd X-Axis)

Tab activation
--------------
  Univariate  : any variable selected
  Bivariate   : has_x AND has_y
  Trivariate  : has_x AND has_y AND has_z

Type helpers
------------
  _is_numeric(t)     — INTERVAL or DATE
  _is_categorical(t) — NOMINAL or ORDINAL (strict)
  _is_cat_like(t)    — NOMINAL, ORDINAL, or LOCATION
                       LOCATION qualifies for all categorical chart rules in the
                       bivariate / multivariate tabs (grouped / stacked columns,
                       heatmap, sankey, mosaic, box / violin / treemap as X,
                       faceted charts as Y facet, small multiples as Z facet),
                       in addition to the tile map chart it already triggers.
                       Individual chart implementations already guard against
                       excessive cardinality.
  _is_date(t)        — DATE only
  _is_location(t)    — LOCATION only
"""

from __future__ import annotations
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType


# ── Type-check helpers ────────────────────────────────────────────────────────

def _is_numeric(vtype: VariableType | None) -> bool:
    """INTERVAL or DATE — continuous axis."""
    return vtype in (VariableType.INTERVAL, VariableType.DATE)


def _is_categorical(vtype: VariableType | None) -> bool:
    """Strictly NOMINAL or ORDINAL (excludes DATE)."""
    return vtype in (VariableType.NOMINAL, VariableType.ORDINAL)


def _is_cat_like(vtype: VariableType | None) -> bool:
    """
    NOMINAL, ORDINAL, or LOCATION.

    LOCATION columns participate in every categorical chart rule for the bivariate
    and multivariate tabs, in addition to the tile map chart they already trigger.
    This lets analysts explore a location column as a grouping variable
    (e.g. box-per-state, heatmap of state × category, small multiples faceted by
    state) without retyping the column.  Chart render() methods already cap or
    warn on high cardinality.
    """
    return vtype in (VariableType.NOMINAL, VariableType.ORDINAL, VariableType.LOCATION)


def _is_date(vtype: VariableType | None) -> bool:
    return vtype == VariableType.DATE


def _is_location(vtype: VariableType | None) -> bool:
    return vtype == VariableType.LOCATION


# ── ChartSelector ─────────────────────────────────────────────────────────────

class ChartSelector:
    """
    Returns the applicable charts for a given VariableSelection.

    Usage
    -----
    selector = ChartSelector()
    applicable = selector.get_applicable_charts(selection)
    # applicable == {"univariate": [...], "bivariate": [...], "trivariate": [...]}
    """

    def get_applicable_charts(
        self,
        selection: VariableSelection,
    ) -> dict[str, list[ChartSpec]]:
        result: dict[str, list[ChartSpec]] = {
            "univariate":  [],
            "bivariate":   [],
            "trivariate":  [],
        }

        x_t = selection.x_type()
        y_t = selection.y_type()

        has_x = selection.x_var is not None
        has_y = selection.y_var is not None
        has_z = selection.group_var is not None

        # ── Univariate ────────────────────────────────────────────────────────
        # Active whenever ANY variable is selected.
        all_selected = [
            (col, selection.var_types.get(col))
            for col in (selection.x_var, selection.y_var, selection.group_var)
            if col is not None
        ]
        _any_selected    = len(all_selected) > 0
        _any_numeric     = any(_is_numeric(vt)     for _, vt in all_selected)
        _any_categorical = any(_is_categorical(vt) for _, vt in all_selected)
        _any_location    = any(_is_location(vt)    for _, vt in all_selected)

        if _any_selected:
            uni: list[ChartSpec] = []
            # Donut & Column — strictly categorical or location only (not date)
            if _any_categorical or _any_location:
                uni.append(ChartSpec("donut_chart",  "univariate", "Donut Chart"))
                uni.append(ChartSpec("column_chart", "univariate", "Column Chart"))
            if _any_numeric:
                uni += [
                    ChartSpec("box_plot",          "univariate", "Box Plot"),
                    ChartSpec("violin_plot",        "univariate", "Violin Plot"),
                    ChartSpec("histogram",          "univariate", "Histogram"),
                    ChartSpec("density_plot",       "univariate", "Density Plot"),
                    ChartSpec("strip_chart",        "univariate", "Strip Chart"),
                    ChartSpec("cumulative_density", "univariate", "Cumulative Density"),
                    ChartSpec("qq_plot",            "univariate", "Q-Q Plot"),
                ]
            result["univariate"] = uni

        # ── Bivariate ─────────────────────────────────────────────────────────
        # Categorical rules use _is_cat_like so DATE qualifies alongside
        # NOMINAL/ORDINAL.  Numeric rules use _is_numeric (unchanged).
        #
        # cat-like × cat-like  → Grouped/Stacked Column, Heatmap, Sankey, Mosaic
        # cat-like × numeric   → Box, Violin, Treemap
        # numeric  × numeric   → Scatter, Hexbin, Correlogram, Line, Stacked Area
        # any      × cat-like  → Faceted Histogram or Faceted Column Chart
        # location × numeric   → US Tile Map
        biv: list[ChartSpec] = []

        if has_x and has_y:
            # ── cat-like × cat-like ───────────────────────────────────────────
            if _is_cat_like(x_t) and _is_cat_like(y_t):
                biv.append(ChartSpec("grouped_column", "bivariate", "Grouped Column Chart"))
                biv.append(ChartSpec("stacked_column", "bivariate", "Stacked Column Chart"))
                biv.append(ChartSpec("heatmap",        "bivariate", "Heatmap"))
                biv.append(ChartSpec("sankey",         "bivariate", "Sankey Diagram"))
                biv.append(ChartSpec("mosaic_plot",    "bivariate", "Mosaic Plot"))

            # ── cat-like × numeric ────────────────────────────────────────────
            if _is_cat_like(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("box_plot",    "bivariate", "Box Plot"))
                biv.append(ChartSpec("violin_plot", "bivariate", "Violin Plot"))
                biv.append(ChartSpec("treemap",     "bivariate", "Treemap"))

            # ── numeric × numeric ─────────────────────────────────────────────
            if _is_numeric(x_t) and _is_numeric(y_t):
                biv += [
                    ChartSpec("scatter_plot", "bivariate", "Scatter Plot"),
                    ChartSpec("hexbin",       "bivariate", "Hexbin Plot"),
                    ChartSpec("correlogram",  "bivariate", "Correlogram"),
                    ChartSpec("line_plot",    "bivariate", "Line Plot"),
                ]

            # ── Date × numeric → Range Line Plot ──────────────────────────────
            if _is_date(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("range_line_plot", "bivariate", "Range Line Plot"))

            # ── Faceted chart: any non-location X, cat-like Y as facet ────────
            # Use strict _is_categorical for naming: DATE x → "Faceted Histogram"
            #   (faceted_histogram.py bins date X as numeric)
            if _is_cat_like(y_t) and not _is_location(x_t):
                facet_name = (
                    "Faceted Column Chart" if _is_categorical(x_t)
                    else "Faceted Histogram"
                )
                biv.append(ChartSpec("faceted_histogram", "bivariate", facet_name))

            # ── US Tile Map: location × numeric ───────────────────────────────
            if _is_location(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("tile_map", "bivariate", "US Tile Map"))

        if biv:
            result["bivariate"] = biv

        # ── Trivariate (X + Y + Z) ────────────────────────────────────────────
        # • Sankey 3-column  — cat-like(x) × cat-like(y) × z (any)
        # • Small Multiples  — numeric(x) × numeric(y) × cat-like(z)
        #   DATE z facets the grid just like a categorical group variable.
        if has_x and has_y and has_z:
            triv: list[ChartSpec] = []
            z_t = selection.group_type()

            if _is_cat_like(x_t) and _is_cat_like(y_t):
                triv.append(ChartSpec("sankey", "trivariate", "Sankey Diagram"))

            if _is_numeric(x_t) and _is_numeric(y_t) and _is_cat_like(z_t):
                triv.append(ChartSpec("small_multiples", "trivariate", "Small Multiples"))
                triv.append(ChartSpec("stacked_area",    "trivariate", "Stacked Area Chart"))

            # ── numeric × numeric × numeric → Line Plot (dual-line) ───────────
            if _is_numeric(x_t) and _is_numeric(y_t) and _is_numeric(z_t):
                triv.append(ChartSpec("line_plot", "trivariate", "Line Plot"))

            if triv:
                result["trivariate"] = triv

        return result
