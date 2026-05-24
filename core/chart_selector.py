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
"""

from __future__ import annotations
from core.chart_config import VariableSelection, ChartSpec
from core.variable_classifier import VariableType


# ── Type-check helpers ────────────────────────────────────────────────────────

def _is_numeric(vtype: VariableType | None) -> bool:
    """Interval/Ratio or Date are treated as numeric for chart purposes."""
    return vtype in (VariableType.INTERVAL, VariableType.DATE)


def _is_categorical(vtype: VariableType | None) -> bool:
    return vtype in (VariableType.NOMINAL, VariableType.ORDINAL)


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
        _any_numeric     = any(_is_numeric(vt)      for _, vt in all_selected)
        _any_categorical = any(_is_categorical(vt)  for _, vt in all_selected)
        _any_location    = any(_is_location(vt)     for _, vt in all_selected)

        if _any_selected:
            uni: list[ChartSpec] = []
            # Donut & Column charts: counts per category — for nominal, ordinal, or location
            if _any_categorical or _any_location:
                uni.append(ChartSpec("donut_chart",   "univariate", "Donut Chart"))
                uni.append(ChartSpec("column_chart",  "univariate", "Column Chart"))
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
        # • cat(x)  + cat(y)     → Grouped/Stacked Column, Heatmap, Sankey, Mosaic,
        #                          Faceted Column Chart
        # • cat(x)  + num(y)     → Box, Violin, Treemap
        # • num(x)  + num(y)     → Scatter, Hexbin, Correlogram, Line, Stacked Area
        # • any(x)  + cat(y)     → Faceted Histogram (num x) / Faceted Column (cat x)
        # • loc(x)  + num(y)     → US Tile Map
        biv: list[ChartSpec] = []

        if has_x and has_y:
            if _is_categorical(x_t) and _is_categorical(y_t):
                biv.append(ChartSpec("grouped_column", "bivariate", "Grouped Column Chart"))
                biv.append(ChartSpec("stacked_column", "bivariate", "Stacked Column Chart"))

            if _is_categorical(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("box_plot",    "bivariate", "Box Plot"))
                biv.append(ChartSpec("violin_plot", "bivariate", "Violin Plot"))
                biv.append(ChartSpec("treemap",     "bivariate", "Treemap"))

            if _is_categorical(x_t) and _is_categorical(y_t):
                biv.append(ChartSpec("heatmap",     "bivariate", "Heatmap"))
                biv.append(ChartSpec("sankey",      "bivariate", "Sankey Diagram"))
                biv.append(ChartSpec("mosaic_plot", "bivariate", "Mosaic Plot"))

            if _is_numeric(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("scatter_plot",  "bivariate", "Scatter Plot"))
                biv.append(ChartSpec("hexbin",        "bivariate", "Hexbin Plot"))
                biv.append(ChartSpec("correlogram",   "bivariate", "Correlogram"))

            if (_is_numeric(x_t) or _is_date(x_t)) and _is_numeric(y_t):
                biv.append(ChartSpec("line_plot",    "bivariate", "Line Plot"))
                biv.append(ChartSpec("stacked_area", "bivariate", "Stacked Area Chart"))

            # Faceted chart: X (any non-location type) faceted by Y (categorical)
            if _is_categorical(y_t) and not _is_location(x_t):
                facet_name = (
                    "Faceted Column Chart" if _is_categorical(x_t)
                    else "Faceted Histogram"
                )
                biv.append(ChartSpec("faceted_histogram", "bivariate", facet_name))

            # US Tile Map: location X + numeric Y
            if _is_location(x_t) and _is_numeric(y_t):
                biv.append(ChartSpec("tile_map", "bivariate", "US Tile Map"))

        if biv:
            result["bivariate"] = biv

        # ── Trivariate (X + Y + Z) ────────────────────────────────────────────
        # • Sankey 3-column        — cat(x) × cat(y) × z (any)
        # • Small Multiples        — numeric/date(x) × numeric/date(y) × cat(z)
        if has_x and has_y and has_z:
            triv: list[ChartSpec] = []
            z_t = selection.group_type()

            if _is_categorical(x_t) and _is_categorical(y_t):
                triv.append(ChartSpec("sankey", "trivariate", "Sankey Diagram"))

            if _is_numeric(x_t) and _is_numeric(y_t) and _is_categorical(z_t):
                triv.append(ChartSpec("small_multiples", "trivariate", "Small Multiples"))

            if triv:
                result["trivariate"] = triv

        return result
