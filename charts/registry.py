"""
Chart registry.

Maps chart_id strings to BaseChart subclasses.  This is the ONLY file that
needs to be modified when adding a new chart type:
  1. Create the chart class file under charts/univariate|bivariate|trivariate/
  2. Import it here and add it to the list below.
  3. Add a rule in core/chart_selector.py for when it should appear.
"""

from charts.base import BaseChart

# ── Univariate ────────────────────────────────────────────────────────────────
from charts.univariate.box_plot        import BoxPlot
from charts.univariate.violin_plot     import ViolinPlot
from charts.univariate.histogram       import Histogram
from charts.univariate.density_plot    import DensityPlot
from charts.univariate.strip_chart     import StripChart
from charts.univariate.cumulative_density import CumulativeDensity
from charts.univariate.qq_plot         import QQPlot
from charts.univariate.donut_chart     import DonutChart
from charts.univariate.column_chart    import ColumnChart

# ── Bivariate ─────────────────────────────────────────────────────────────────
from charts.bivariate.faceted_histogram import FacetedHistogram
from charts.bivariate.grouped_column   import GroupedColumn
from charts.bivariate.stacked_column   import StackedColumn
from charts.bivariate.scatter_plot     import ScatterPlot
from charts.bivariate.hexbin           import Hexbin
from charts.bivariate.correlogram      import Correlogram
from charts.bivariate.line_plot        import LinePlot
from charts.bivariate.treemap          import Treemap
from charts.bivariate.tile_map         import TileMap

# ── Trivariate ────────────────────────────────────────────────────────────────
from charts.trivariate.sankey          import Sankey
from charts.trivariate.mosaic_plot     import MosaicPlot
from charts.trivariate.small_multiples import SmallMultiples
from charts.trivariate.heatmap         import Heatmap
from charts.trivariate.stacked_area    import StackedArea


# All registered chart classes — one entry per chart type
_ALL_CHART_CLASSES: list[type[BaseChart]] = [
    # Univariate
    BoxPlot, ViolinPlot, Histogram, DensityPlot, StripChart, CumulativeDensity, QQPlot,
    DonutChart, ColumnChart,
    # Bivariate
    FacetedHistogram,
    GroupedColumn, StackedColumn, ScatterPlot, Hexbin, Correlogram, LinePlot, Treemap,
    TileMap,
    # Trivariate
    Sankey, MosaicPlot, SmallMultiples, Heatmap, StackedArea,
]

CHART_REGISTRY: dict[str, type[BaseChart]] = {
    cls.CHART_ID: cls
    for cls in _ALL_CHART_CLASSES
}
