# chartBuilder

A local Python desktop application for interactive chart exploration. Import a CSV or Excel file, select up to three typed variables, optionally clean or transform them, and get an instant dashboard of all applicable charts — organised by dimensionality.

---

## Table of Contents

1. [Getting Started](#1-getting-started)
2. [Workflow](#2-workflow)
3. [Variable Slots](#3-variable-slots)
4. [Variable Types](#4-variable-types)
5. [Transforms](#5-transforms)
6. [Cleaning Values](#6-cleaning-values)
7. [Chart Dashboard](#7-chart-dashboard)
8. [Chart Types Reference](#8-chart-types-reference)
9. [Editing Charts](#9-editing-charts)
10. [Exporting Charts](#10-exporting-charts)
11. [Developer Guide](#11-developer-guide)

---

## 1. Getting Started

**Requirements:** Python ≥ 3.13, macOS or Windows.

Install dependencies (all are likely already present):

```bash
pip install -r requirements.txt
```

Launch the application:

```bash
cd "/path/to/chartBuilder"
python3 main.py
```

---

## 2. Workflow

```
① Load file  →  ② Select variables  →  ③ Clean / transform  →  ④ Browse charts  →  ⑤ Edit & export
```

The application is **reactive** — charts update automatically within 300 ms of any variable change. There is no "Run" button.

---

## 3. Variable Slots

The left panel contains three named variable slots. Each slot has:

| Control | Purpose |
|---|---|
| **Variable dropdown** | Pick a column from the loaded dataset |
| **Type selector** | Override the auto-detected variable type |
| **▼ Transform** | Apply a mathematical transformation before charting |
| **Clean** | Filter out values or merge categories |

### The three slots

| Slot | Required | Role |
|---|---|---|
| **X-Axis** | ✓ | Independent variable — the horizontal axis |
| **Y-Axis** | — | Dependent variable — the vertical axis |
| **Z-Axis** | — | Third variable — used for faceting (Small Multiples), Sankey flow sections (3-column), and scatter-plot colouring |

**Minimum for charts:**
- Univariate charts require any single variable selected
- Bivariate charts require **X-Axis + Y-Axis**
- Multivariate charts require **X-Axis + Y-Axis + Z-Axis**

---

## 4. Variable Types

chartBuilder auto-detects variable types on import. You can override any type using the dropdown next to each variable.

| Type | When to use |
|---|---|
| **Nominal** | Categories with no inherent order (e.g. Gender, Country) |
| **Ordinal** | Ordered categories (e.g. Likert scales 1–5, Education levels) |
| **Interval/Ratio** | Numeric continuous data (e.g. Income, Age, Temperature) |
| **Date** | Date or datetime columns (e.g. 2024-01-15, Jan 2024) |

**Auto-detection rules (in priority order):**
1. Object/string column where ≥ 80% of values parse as dates → **Date**
2. Boolean column → **Nominal**
3. Object column where ≥ 80% of values coerce to numbers → Nominal/Ordinal/Interval based on cardinality
4. Object column that doesn't coerce → **Nominal**
5. Numeric column with > 50% unique values or > 20 distinct values → **Interval/Ratio**
6. Numeric column matching a Likert-style integer scale (e.g. 1–5, 0–7) → **Ordinal**
7. Numeric column with ≤ 15 unique values → **Ordinal**
8. Everything else → **Interval/Ratio**

The auto-detection is a heuristic — always override if the result looks wrong.

---

## 5. Transforms

Click the **▼ Transform** button next to any variable to apply a mathematical transformation before charting. The column name is unchanged; axis labels will note the transformation (e.g. "Income (Natural Log)").

| Transform | Formula | Common use |
|---|---|---|
| **None** | Identity | Default |
| **Natural Log** | ln(x) | Normalise right-skewed data; removes outlier pull |
| **Percent Change** | (xₙ − xₙ₋₁) / xₙ₋₁ × 100 | Growth rates in time-series |
| **First Difference** | xₙ − xₙ₋₁ | Remove trends from time-series |
| **Lag 1 Period** | shift(1) | Autocorrelation analysis |
| **Lag 2 Periods** | shift(2) | |
| **Lag 3 Periods** | shift(3) | |

> **Note:** Transforms that introduce NaN (log of zero/negative, lag at series edges) preserve row alignment — those rows will simply appear as missing in charts.

---

## 6. Cleaning Values

Click the **Clean** button on any variable slot to open the **Clean Values** dialog.

The dialog shows a three-column table:

| Column | Purpose |
|---|---|
| **Include** | Uncheck to exclude this value entirely from all charts |
| **Original Value** | The raw value from the dataset (read-only) |
| **New Group Name** | Rename or merge values by giving them the same name |

**Tips:**
- Click the **Include** column header to select / deselect all rows at once
- Click anywhere in the **Original Value** column to toggle that row's checkbox
- Use **Set selected rows to:** to bulk-rename multiple selected rows
- **Reset to original** restores all names to their original values

The Clean mapping is preserved when you change other variables, so you can set it once and keep it.

---

## 7. Chart Dashboard

The right panel is a three-tab chart dashboard:

| Tab | What it shows | Minimum variables needed |
|---|---|---|
| **Univariate** | Distribution of a single variable | Any one variable selected |
| **Bivariate** | Relationship between two variables | X-Axis + Y-Axis |
| **Multivariate** | Three-way relationships and faceted scatter/line charts | X-Axis + Y-Axis + Z-Axis |

Tabs are greyed out when the required variables aren't selected. The application automatically switches to the first tab that has applicable charts.

### Within each tab

- **Chart dropdown** — select which chart to display from all applicable options
- **Variable picker** — (Univariate tab) choose which selected variable to display when more than one is selected
- **Toolbar** — pan, zoom, and reset the chart (matplotlib navigation bar)
- **Quick Edit** — open the chart options dialog to change titles, colours, and toggles
- **Export PNG** — save the current chart at 300 DPI

---

## 8. Chart Types Reference

### Univariate

The **Variable:** picker in the Univariate tab lets you choose which selected variable to display.

| Chart | Variable types | Description | Best for |
|---|---|---|---|
| **Donut Chart** | Nominal / Ordinal | Proportional wedges per category | Quick share-of-whole for categorical variables |
| **Column Chart** | Nominal / Ordinal | Bar chart of value counts, sorted by count or value | Comparing category frequencies |
| **Box Plot** | Numeric / Date | Median, quartiles, and outliers; date axes auto-formatted | Quick distribution summary |
| **Violin Plot** | Numeric / Date | Box plot + kernel density silhouette; date axes auto-formatted | Distribution shape comparison |
| **Histogram** | Numeric / Date | Binned frequency counts (Freedman-Diaconis rule); date axes auto-formatted | Full distribution shape |
| **Density Plot** | Numeric / Date | Smoothed kernel density estimate; date axes auto-formatted | Smooth distribution comparison |
| **Strip Chart** | Numeric / Date | Jittered dot plot showing individual points; date axes auto-formatted | Small datasets, seeing every value |
| **Cumulative Density** | Numeric / Date | ECDF — proportion of values below each point; date axes auto-formatted | Percentile analysis |
| **Q-Q Plot** | Numeric / Date | Sample quantiles vs. Normal theoretical quantiles; date axes auto-formatted | Normality check |

### Bivariate

| Chart | X type | Y type | Notes |
|---|---|---|---|
| **Grouped Column Chart** | Categorical | Numeric or Categorical | Means (numeric Y) or grouped counts (categorical Y) |
| **Stacked Column Chart** | Categorical | Numeric or Categorical | Supports 100% normalised stacking |
| **Box Plot** | Categorical | Numeric | Distribution of Y per X category |
| **Violin Plot** | Categorical | Numeric | Distribution shape of Y per X category |
| **Treemap** | Categorical | Numeric | Proportional size comparison |
| **Heatmap** | Categorical | Categorical | Cell-level counts |
| **Sankey Diagram** | Categorical | Categorical | 2-column flow (X → Y); gray node bars, coloured bezier flows |
| **Mosaic Plot** | Categorical | Categorical | Proportional area; cells labelled with count & % |
| **Scatter Plot** | Numeric / Date | Numeric / Date | Z-Axis colours points when set (categorical → legend, numeric → colorbar); date axes auto-formatted |
| **Hexbin Plot** | Numeric / Date | Numeric / Date | Scatter for large datasets with many overlapping points; date axes auto-formatted |
| **Correlogram** | Numeric | Numeric | Pairwise correlations across all numeric columns in the dataset |
| **Line Plot** | Numeric or Date | Numeric | Trends over a continuous or time axis |
| **Stacked Area Chart** | Numeric or Date | Numeric | Cumulative trends over time |
| **Faceted Histogram** | Numeric | Categorical | Distribution of X (numeric) in a separate panel per Y category |
| **Faceted Column Chart** | Categorical | Categorical | Bar chart of X counts in a separate panel per Y category |
| **Mosaic Plot** | Categorical | Categorical | Proportional area; Y-Axis categories share a consistent colour across all X categories |

### Multivariate (X + Y + Z required)

| Chart | X type | Y type | Z type | Best for |
|---|---|---|---|---|
| **Sankey Diagram** | Categorical | Categorical | Any | 3-column flow (X → Y → Z); gray node bars, coloured bezier flows |
| **Small Multiples** | Numeric / Date | Numeric / Date | Categorical | Scatter or Line panels of Y vs X, one panel per Z category |

> **Scatter Plot Z-Axis colouring:** when Z-Axis is set, scatter points are coloured by that variable. Categorical Z → distinct colours + legend. Numeric Z → viridis gradient + colour bar.
>
> **Small Multiples:** facet sort order (Ascending / Descending / As-is), sub-chart type (Scatter / Line), shared axis ranges, and same-colour-across-panels are all configurable via **Quick Edit**.

---

## 9. Editing Charts

Click **Quick Edit** to open the chart options dialog. The available options depend on the chart type, but commonly include:

| Option type | Examples |
|---|---|
| **Text** | Chart title, X-axis label, Y-axis label |
| **Toggle (on/off)** | Show trend line, show error bars, show confidence band, fill under curve |
| **Palette choice** | Colour scheme (tab10, Blues, viridis, RdBu_r, etc.) |

Edit options **persist** when you change variables, so a title you set stays set even if you switch X-Axis columns.

Click **Apply** to update the chart immediately.

---

## 10. Exporting Charts

Click **Export PNG** in any chart tab. A save dialog will appear. Charts are exported at **300 DPI** (print quality).

The filename defaults to the chart ID (e.g. `histogram.png`). Change it to anything you like in the dialog.

---

## 11. Developer Guide

### Architecture

```
chartBuilder/
├── main.py                    # Entry point
├── core/                      # Pure Python — no GUI imports
│   ├── data_loader.py         # CSV/XLSX/XLS loading
│   ├── variable_classifier.py # Auto-classify columns (Nominal/Ordinal/Interval/Date)
│   ├── transformer.py         # Per-variable transforms (log, lag, diff, %)
│   ├── consolidator.py        # Value filter/recode logic
│   ├── chart_config.py        # VariableSelection, ChartSpec dataclasses
│   ├── chart_selector.py      # Applicability logic: which charts for which types?
│   └── exporter.py            # PNG export at 300 DPI
│
├── charts/                    # One file per chart type
│   ├── base.py                # BaseChart abstract class
│   ├── registry.py            # CHART_REGISTRY — only file to edit when adding a chart
│   ├── univariate/            # 9 chart modules
│   ├── bivariate/             # 9 chart modules (Box + Violin render bivariate from univariate/)
│   └── trivariate/            # 4 chart modules
│
└── ui/
    ├── palette.py             # All colours + APP_STYLESHEET
    ├── main_window.py         # Signal router / orchestrator
    ├── panels/
    │   ├── file_panel.py      # File browse + sheet selector
    │   ├── variable_panel.py  # 3 VariableSlot widgets (X, Y, Z)
    │   └── chart_dashboard.py # 3-tab chart view
    └── dialogs/
        ├── consolidate_dialog.py  # Clean values dialog
        └── chart_edit_dialog.py   # Chart options editor
```

### Signal flow

```
FilePanel.data_loaded(df, path)
  → MainWindow._on_data_loaded()
      VariableClassifier.classify_all(df)          → auto-detected types
      warn if len(df) > 100,000                     → yellow banner
      VariablePanel.set_data(df, auto_types)
      ChartDashboard.clear()

VariablePanel.selection_changed(VariableSelection)  ← 300 ms debounced
  → MainWindow._on_selection_changed()
      ResponseConsolidator.apply(df)               → filtered/recoded df
      VariableTransformer.apply_all(df, transforms) → transformed df
      ChartSelector.get_applicable_charts(sel)      → applicable chart lists
      ChartDashboard.set_data(df_work, sel, applicable)
```

### Adding a new chart type

**Step 1 — Create the chart module**

```python
# charts/univariate/my_chart.py
from charts.base import BaseChart
from core.chart_config import VariableSelection, ChartSpec

class MyChart(BaseChart):
    CHART_ID       = "my_chart"      # unique snake_case identifier
    DISPLAY_NAME   = "My Chart"      # shown in the UI dropdown
    DIMENSIONALITY = "univariate"    # "univariate" | "bivariate" | "trivariate"

    @classmethod
    def get_spec(cls) -> ChartSpec:
        return ChartSpec(cls.CHART_ID, cls.DIMENSIONALITY, cls.DISPLAY_NAME)

    def _default_edit_options(self) -> dict:
        return {
            "title":   {"label": "Title",     "type": "text",   "default": ""},
            "palette": {"label": "Palette",   "type": "choice",
                        "default": "tab10",   "choices": ["tab10", "Blues", "viridis"]},
            "show_grid":{"label": "Show grid","type": "bool",   "default": True},
        }

    def render(self, df, selection: VariableSelection, fig) -> None:
        fig.clear()
        ax = fig.add_subplot(111)
        # ... matplotlib drawing code ...
        ax.set_title(self._opt("title") or f"My Chart — {selection.x_var}",
                     fontsize=13, fontweight="bold")
        self._apply_figure_style(fig, ax)
        fig.tight_layout()
```

**Step 2 — Register it** (one line in `charts/registry.py`):

```python
from charts.univariate.my_chart import MyChart

_ALL_CHART_CLASSES = [
    # ... existing charts ...
    MyChart,   # ← add here
]
```

**Step 3 — Add an applicability rule** in `core/chart_selector.py`:

```python
# Example: add to the univariate block when any categorical var is selected
if _any_categorical:
    uni.append(ChartSpec("my_chart", "univariate", "My Chart"))
```

That's it. No other files need changing.

### Inherited helpers in BaseChart

| Method | What it does |
|---|---|
| `self._opt(key)` | Returns the current value of an edit option (user value or default) |
| `self._apply_figure_style(fig, ax)` | Applies consistent spine colour, grid, and font styling |
| `self._large_data_sample(df, limit)` | Returns `(df_sample, was_sampled)` — use for slow charts |
| `self._add_sample_note(ax, n)` | Adds an annotation noting that a sample was used |

### VariableSelection fields

```python
@dataclass
class VariableSelection:
    x_var:     Optional[str]            # X-Axis column name
    y_var:     Optional[str]            # Y-Axis column name
    group_var: Optional[str]            # Z-Axis column name
    var_types:      dict[str, VariableType]   # type per column (may include overrides)
    transforms:     dict[str, TransformType]  # active transform per column
    consolidations: dict[str, dict]           # clean/recode mappings per column
```

Convenience methods: `x_type()`, `y_type()`, `group_type()`, `x_transform()`, `y_transform()`, `selected_vars()`, `has_bivariate()`, `has_trivariate()`.

### Changing the colour scheme

All colours live in `ui/palette.py`. Edit the constants there — the QSS stylesheet is regenerated automatically at startup. No other files need touching.

```python
# ui/palette.py
PRIMARY       = "#2563EB"   # buttons, focus rings, active tabs
PRIMARY_HOVER = "#1D4ED8"
GREY_700      = "#334155"   # primary text
# ... etc.

# Chart colours
MPL_DEFAULT_PALETTE = "tab10"
MPL_ACCENT          = "#2563EB"
MPL_TREND           = "#DC2626"
PALETTE_CHOICES     = ["tab10", "tab20", "Blues", ...]  # shown in Edit dialog
```

### Large data handling

- Files with > 100,000 rows: a persistent yellow warning banner appears
- Charts that are slow on large data (Violin, Q-Q, Strip, Density, Scatter) automatically sample to **50,000 rows** for rendering and annotate the figure: *"Showing a random sample of 50,000 rows"*
- The sample is deterministic (random seed = 42) so it is consistent across re-renders

### Future: linking with crosstabs

`DataLoader`, `VariableClassifier`, and `ResponseConsolidator` share identical public APIs in both chartBuilder and the sibling `crosstabs` application.

When you are ready to link the two apps:
1. Create a `shared/` package alongside both project folders
2. Move those three modules into it
3. Update `import` paths in both apps — no logic changes required

### Running tests

There are no formal tests yet. Use the test data for quick manual verification:

```bash
cd "/path/to/chartBuilder"
python3 -c "
from core.data_loader import DataLoader
df = DataLoader().load('testing/test_data.xlsx')
print(df.shape, list(df.columns))
"
```

---

## Notes

- **All processing is local.** No data leaves your machine.
- The **crosstabs folder is never modified** by chartBuilder — the two apps are fully independent.
- The font warning `"Segoe UI" not found` on macOS is harmless — Qt falls back to the system font automatically.
