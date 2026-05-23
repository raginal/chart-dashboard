"""
Global colour palette and application stylesheet for chartBuilder.

Modify the constants here to restyle the entire application without
touching any panel code.  All colour strings must be valid CSS hex values.

Chart palette constants (MPL_*) are used directly in chart render() methods
and in the palette selector shown in ChartEditDialog.
"""

# ── Neutral greys (Tailwind CSS "Slate" scale) ─────────────────────────────
GREY_50  = "#F8FAFC"   # page / panel background
GREY_100 = "#F1F5F9"   # subtle element backgrounds
GREY_200 = "#E2E8F0"   # borders, dividers
GREY_400 = "#94A3B8"   # placeholder text, icon tint
GREY_500 = "#64748B"   # secondary text
GREY_700 = "#334155"   # primary text
GREY_900 = "#0F172A"   # near-black headings

# ── Primary action colour ───────────────────────────────────────────────────
PRIMARY       = "#2563EB"   # buttons, focus rings, active tabs
PRIMARY_HOVER = "#1D4ED8"
PRIMARY_LIGHT = "#EFF6FF"   # light-blue tint for active rows / highlights
PRIMARY_TEXT  = "#FFFFFF"

# ── Semantic colours ────────────────────────────────────────────────────────
WARN_BG   = "#FEFCE8"   # warning banner background (>100k rows)
WARN_TEXT = "#92400E"   # warning banner text

# ── Matplotlib / chart palette ──────────────────────────────────────────────
# Named seaborn/matplotlib palettes available in the chart edit dialog.
MPL_DEFAULT_PALETTE  = "tab10"      # categorical default (distinct hues)
MPL_SEQUENTIAL       = "Blues"      # single-variable distributions
MPL_DIVERGING        = "RdBu_r"     # diverging / correlation charts
MPL_ACCENT           = "#2563EB"    # single-series accent colour (primary)
MPL_TREND            = "#DC2626"    # trend / regression line colour
MPL_CONFIDENCE_BAND  = "#BFDBFE"    # confidence band fill (blue-100)

# Palette choices offered in ChartEditDialog
PALETTE_CHOICES = [
    "tab10", "tab20", "Set1", "Set2", "Set3",
    "Paired", "Blues", "Greens", "Reds", "Oranges",
    "viridis", "plasma", "RdBu_r", "coolwarm",
]

# ── Application-wide Qt Style Sheet ─────────────────────────────────────────
# Flat design: no gradients, subtle borders, consistent border-radius.
APP_STYLESHEET = f"""
/* ── Base ── */
QMainWindow, QDialog {{
    background-color: {GREY_50};
    color: {GREY_700};
}}

QWidget {{
    font-family: "Segoe UI", "Helvetica Neue", Arial, sans-serif;
    font-size: 13px;
    color: {GREY_700};
}}

/* ── Group boxes ── */
QGroupBox {{
    font-weight: 600;
    border: 1px solid {GREY_200};
    border-radius: 6px;
    margin-top: 12px;
    padding: 6px 8px 8px 8px;
    background-color: #FFFFFF;
}}
QGroupBox::title {{
    subcontrol-origin: margin;
    subcontrol-position: top left;
    padding: 0 6px;
    color: {GREY_500};
    background-color: {GREY_50};
    font-size: 12px;
}}

/* ── Buttons ── */
QPushButton {{
    background-color: {GREY_100};
    color: {GREY_700};
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 4px 14px;
    min-height: 26px;
}}
QPushButton:hover {{
    background-color: {GREY_200};
    border-color: {GREY_400};
}}
QPushButton:pressed {{
    background-color: {GREY_200};
}}
QPushButton:disabled {{
    color: {GREY_400};
    background-color: {GREY_100};
    border-color: {GREY_200};
}}

/* Primary action button — objectName="primary_btn" */
QPushButton#primary_btn {{
    background-color: {PRIMARY};
    color: {PRIMARY_TEXT};
    border: none;
    border-radius: 5px;
    font-size: 13px;
    font-weight: 600;
}}
QPushButton#primary_btn:hover {{
    background-color: {PRIMARY_HOVER};
}}
QPushButton#primary_btn:disabled {{
    background-color: {GREY_400};
    color: {GREY_100};
}}

/* Warning banner label — objectName="warn_banner" */
QLabel#warn_banner {{
    background-color: {WARN_BG};
    color: {WARN_TEXT};
    border: 1px solid #FDE68A;
    border-radius: 4px;
    padding: 4px 8px;
    font-size: 12px;
    font-weight: 500;
}}

/* ── Dropdowns ── */
QComboBox {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 3px 8px;
    background-color: #FFFFFF;
    min-height: 26px;
    selection-background-color: {PRIMARY_LIGHT};
}}
QComboBox:focus {{
    border-color: {PRIMARY};
}}
QComboBox::drop-down {{
    border: none;
    width: 20px;
}}
QComboBox QAbstractItemView {{
    border: 1px solid {GREY_200};
    selection-background-color: {PRIMARY_LIGHT};
    selection-color: {PRIMARY};
}}
QComboBox:disabled {{
    background-color: {GREY_100};
    color: {GREY_400};
}}

/* ── Line edits ── */
QLineEdit {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 3px 8px;
    background-color: #FFFFFF;
    min-height: 26px;
}}
QLineEdit:focus {{
    border-color: {PRIMARY};
}}
QLineEdit[readOnly="true"] {{
    background-color: {GREY_100};
    color: {GREY_500};
}}

/* ── Tabs ── */
QTabWidget::pane {{
    border: 1px solid {GREY_200};
    border-radius: 0 6px 6px 6px;
    background-color: #FFFFFF;
}}
QTabBar::tab {{
    background-color: {GREY_100};
    color: {GREY_500};
    border: 1px solid {GREY_200};
    border-bottom: none;
    border-radius: 5px 5px 0 0;
    padding: 6px 20px;
    margin-right: 2px;
    font-size: 13px;
    min-width: 100px;
}}
QTabBar::tab:selected {{
    background-color: #FFFFFF;
    color: {PRIMARY};
    border-bottom: 2px solid {PRIMARY};
    font-weight: 700;
}}
QTabBar::tab:hover:!selected {{
    background-color: {GREY_200};
    color: {GREY_700};
}}
QTabBar::tab:disabled {{
    color: #B0BAC6;
    background-color: {GREY_50};
    font-style: italic;
    border-color: {GREY_200};
}}

/* ── Table ── */
QTableWidget {{
    border: 1px solid {GREY_200};
    gridline-color: {GREY_200};
    background-color: #FFFFFF;
    alternate-background-color: {GREY_50};
}}
QHeaderView::section {{
    background-color: {GREY_100};
    border: 1px solid {GREY_200};
    padding: 4px 8px;
    font-weight: 600;
    color: {GREY_700};
}}

/* ── Scroll area ── */
QScrollArea {{
    border: none;
    background-color: {GREY_50};
}}

/* ── Scroll bars (flat — overrides Fusion gradient) ── */
QScrollBar:vertical {{
    border: none;
    background-color: {GREY_100};
    width: 10px;
    margin: 0px;
}}
QScrollBar::handle:vertical {{
    background-color: {GREY_200};
    border-radius: 5px;
    min-height: 24px;
}}
QScrollBar::handle:vertical:hover {{
    background-color: {GREY_400};
}}
QScrollBar::add-line:vertical,
QScrollBar::sub-line:vertical {{
    height: 0px;
    background: none;
}}
QScrollBar::add-page:vertical,
QScrollBar::sub-page:vertical {{
    background: none;
}}
QScrollBar:horizontal {{
    border: none;
    background-color: {GREY_100};
    height: 10px;
    margin: 0px;
}}
QScrollBar::handle:horizontal {{
    background-color: {GREY_200};
    border-radius: 5px;
    min-width: 24px;
}}
QScrollBar::handle:horizontal:hover {{
    background-color: {GREY_400};
}}
QScrollBar::add-line:horizontal,
QScrollBar::sub-line:horizontal {{
    width: 0px;
    background: none;
}}
QScrollBar::add-page:horizontal,
QScrollBar::sub-page:horizontal {{
    background: none;
}}

/* ── Status bar ── */
QStatusBar {{
    background-color: {GREY_100};
    color: {GREY_500};
    font-size: 11px;
    border-top: 1px solid {GREY_200};
}}

/* ── Checkboxes ── */
QCheckBox::indicator {{
    width: 15px;
    height: 15px;
    border: 1.5px solid {GREY_400};
    border-radius: 3px;
    background-color: #FFFFFF;
}}
QCheckBox::indicator:checked {{
    background-color: {PRIMARY};
    border-color: {PRIMARY};
}}

/* ── Radio buttons ── */
QRadioButton::indicator {{
    width: 14px;
    height: 14px;
    border: 1.5px solid {GREY_400};
    border-radius: 7px;
    background-color: #FFFFFF;
}}
QRadioButton::indicator:checked {{
    border-color: {PRIMARY};
    background-color: {PRIMARY};
}}

/* ── Text edit ── */
QTextEdit {{
    border: 1px solid {GREY_200};
    border-radius: 4px;
    background-color: #FFFFFF;
    padding: 4px;
}}

/* ── Splitter ── */
QSplitter::handle {{
    background-color: {GREY_200};
    width: 1px;
}}

/* ── Label (plain) ── */
QLabel {{
    background-color: transparent;
}}

/* ── Toolbar (matplotlib nav) ── */
QToolBar {{
    background-color: {GREY_50};
    border: none;
    spacing: 2px;
}}
QToolButton {{
    background-color: transparent;
    border: 1px solid transparent;
    border-radius: 4px;
    padding: 2px;
}}
QToolButton:hover {{
    background-color: {GREY_100};
    border-color: {GREY_200};
}}

/* ── Menu (transform QMenu) ── */
QMenu {{
    background-color: #FFFFFF;
    border: 1px solid {GREY_200};
    border-radius: 4px;
    padding: 4px;
}}
QMenu::item {{
    padding: 6px 24px 6px 12px;
    border-radius: 3px;
}}
QMenu::item:selected {{
    background-color: {PRIMARY_LIGHT};
    color: {PRIMARY};
}}
QMenu::item:checked {{
    font-weight: 600;
    color: {PRIMARY};
}}
"""
