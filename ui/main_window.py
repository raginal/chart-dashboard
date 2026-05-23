"""
MainWindow — top-level orchestrator for chartBuilder.

Layout
------
QSplitter (horizontal):
  Left  → QScrollArea containing FilePanel + VariablePanel
  Right → ChartDashboard (three-tab chart view)

Signal flow
-----------
FilePanel.data_loaded(df, path)
  → _on_data_loaded()
      classify all columns
      warn if > 100k rows
      VariablePanel.set_data()
      ChartDashboard.clear()

VariablePanel.selection_changed(VariableSelection)
  → 300 ms debounce (in VariablePanel) → _on_selection_changed()
      consolidator.apply(df)
      transformer.apply_all(df_work, transforms)
      chart_selector.get_applicable_charts(selection)
      ChartDashboard.set_data()
"""
from __future__ import annotations
from typing import Optional

import pandas as pd
from PyQt6.QtWidgets import (
    QMainWindow, QWidget, QSplitter, QScrollArea,
    QVBoxLayout, QLabel, QStatusBar, QMessageBox,
)
from PyQt6.QtCore import Qt

from core.variable_classifier import VariableClassifier
from core.consolidator import ResponseConsolidator
from core.transformer import VariableTransformer
from core.chart_selector import ChartSelector
from core.chart_config import VariableSelection
from ui.panels.file_panel import FilePanel
from ui.panels.variable_panel import VariablePanel
from ui.panels.chart_dashboard import ChartDashboard
from ui.palette import WARN_BG, WARN_TEXT, GREY_50, GREY_200

ROW_WARN_THRESHOLD   = 100_000
LEFT_PANEL_MIN_WIDTH = 380
LEFT_PANEL_MAX_WIDTH = 480


class MainWindow(QMainWindow):
    """Top-level window — signal router and state owner."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("chartBuilder")
        self.setMinimumSize(1100, 700)
        self.resize(1400, 850)

        # ── Core processors ───────────────────────────────────────────────────
        self._classifier  = VariableClassifier()
        self._consolidator = ResponseConsolidator()
        self._transformer  = VariableTransformer()
        self._chart_selector = ChartSelector()

        # ── State ─────────────────────────────────────────────────────────────
        self._df: Optional[pd.DataFrame] = None

        # ── Build UI ──────────────────────────────────────────────────────────
        self._build_ui()

    # ── UI Construction ───────────────────────────────────────────────────────

    def _build_ui(self) -> None:
        # Central widget + splitter
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        splitter.setHandleWidth(1)
        root.addWidget(splitter)

        # ── Left panel ────────────────────────────────────────────────────────
        left_container = QWidget()
        left_layout = QVBoxLayout(left_container)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.setSpacing(0)

        # Large-data warning banner (hidden by default)
        self._warn_banner = QLabel(
            "⚠  This dataset has over 100,000 rows. "
            "Some charts may be slow to render."
        )
        self._warn_banner.setObjectName("warn_banner")
        self._warn_banner.setWordWrap(True)
        self._warn_banner.setVisible(False)
        left_layout.addWidget(self._warn_banner)

        # Scrollable left panel content
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll.setStyleSheet(f"background: {GREY_50};")

        scroll_content = QWidget()
        scroll_layout  = QVBoxLayout(scroll_content)
        scroll_layout.setContentsMargins(10, 10, 10, 10)
        scroll_layout.setSpacing(10)

        self.file_panel     = FilePanel()
        self.variable_panel = VariablePanel()

        scroll_layout.addWidget(self.file_panel)
        scroll_layout.addWidget(self.variable_panel)
        scroll_layout.addStretch()

        scroll.setWidget(scroll_content)
        left_layout.addWidget(scroll, 1)

        left_container.setMinimumWidth(LEFT_PANEL_MIN_WIDTH)
        left_container.setMaximumWidth(LEFT_PANEL_MAX_WIDTH)
        splitter.addWidget(left_container)

        # ── Right panel ───────────────────────────────────────────────────────
        self.chart_dashboard = ChartDashboard()
        splitter.addWidget(self.chart_dashboard)

        # Splitter proportions: left panel fixed width, right panel expands
        splitter.setStretchFactor(0, 0)
        splitter.setStretchFactor(1, 1)
        splitter.setSizes([440, 960])

        # ── Status bar ────────────────────────────────────────────────────────
        self._status = QStatusBar()
        self.setStatusBar(self._status)
        self._status.showMessage("No data loaded.")

        # ── Wire signals ──────────────────────────────────────────────────────
        self.file_panel.data_loaded.connect(self._on_data_loaded)
        self.variable_panel.selection_changed.connect(self._on_selection_changed)

    # ── Signal handlers ───────────────────────────────────────────────────────

    def _on_data_loaded(self, df: pd.DataFrame, path: str) -> None:
        """Called when the FilePanel successfully loads a file."""
        self._df = df
        self._consolidator.clear()

        # Classify all columns
        auto_types = self._classifier.classify_all(df)

        # Large-data warning
        n_rows = len(df)
        if n_rows > ROW_WARN_THRESHOLD:
            self._warn_banner.setText(
                f"⚠  This dataset has {n_rows:,} rows. "
                "Some charts may be slow. A 50,000-row sample will be used where needed."
            )
            self._warn_banner.setVisible(True)
        else:
            self._warn_banner.setVisible(False)

        # Populate variable panel
        self.variable_panel.set_data(df, auto_types)

        # Clear the chart area
        self.chart_dashboard.clear()

        n_cols = len(df.columns)
        self._status.showMessage(
            f"Loaded {n_rows:,} rows × {n_cols} columns from {path.split('/')[-1]}"
        )

    def _on_selection_changed(self, selection: VariableSelection) -> None:
        """
        Called (debounced) whenever the user changes any variable slot.
        Runs the full data pipeline and updates the chart dashboard.
        """
        if self._df is None:
            return

        if selection.x_var is None:
            self.chart_dashboard.clear()
            self._status.showMessage("Select an X-Axis variable to begin.")
            return

        try:
            # 1. Apply value consolidations (filter / recode)
            #    Merge slot-level consolidators into the global one
            self._consolidator.set_from_dict(selection.consolidations)
            df_work = self._consolidator.apply(self._df)

            # 2. Apply per-variable transforms
            df_work = self._transformer.apply_all(df_work, selection.transforms)

            # 3. Determine applicable charts
            applicable = self._chart_selector.get_applicable_charts(selection)

            total_charts = sum(len(v) for v in applicable.values())
            if total_charts == 0:
                self.chart_dashboard.clear()
                self._status.showMessage(
                    "No charts available for the selected variable types. "
                    "Try changing variable types."
                )
                return

            # 4. Send to dashboard
            self.chart_dashboard.set_data(df_work, selection, applicable)

            # Status summary
            parts = []
            for dim, specs in applicable.items():
                if specs:
                    parts.append(f"{len(specs)} {dim}")
            self._status.showMessage(
                f"Showing: {', '.join(parts)} chart{'s' if total_charts != 1 else ''}."
            )

        except Exception as exc:
            QMessageBox.critical(self, "Error", f"Could not update charts:\n{exc}")
