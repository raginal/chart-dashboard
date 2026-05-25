"""
Chart dashboard — the right-side panel.

Contains three QTabWidget tabs (Univariate / Bivariate / Trivariate).
Each tab is a ChartTabPane that holds:
  - A chart selector dropdown
  - An embedded matplotlib FigureCanvas
  - A NavigationToolbar
  - Export PNG and Edit buttons

Chart instances are created lazily and persist for the session so that
edit options survive variable changes.
"""
from __future__ import annotations
from dataclasses import replace as dc_replace
from typing import Optional
from pathlib import Path

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QTabWidget, QSizePolicy, QFileDialog, QMessageBox,
)
from PyQt6.QtCore import Qt

from matplotlib.backends.backend_qtagg import FigureCanvasQTAgg, NavigationToolbar2QT
from matplotlib.figure import Figure

from charts.base import BaseChart
from charts.registry import CHART_REGISTRY
from core.chart_config import VariableSelection, ChartSpec
from core.chart_selector import ChartSelector
from core.variable_classifier import VariableType
from core.exporter import Exporter
from ui.dialogs.chart_edit_dialog import ChartEditDialog
from ui.palette import GREY_400, GREY_500, GREY_50


class ChartTabPane(QWidget):
    """
    One dimensionality tab (e.g. Univariate).

    Owns a subset of chart instances and renders the user-selected chart
    into a matplotlib canvas.
    """

    def __init__(self, dimensionality: str, parent=None):
        super().__init__(parent)
        self._dimensionality   = dimensionality
        self._chart_specs:     list[ChartSpec] = []
        self._chart_instances: dict[str, BaseChart] = {}
        self._current_df:      Optional[pd.DataFrame] = None
        self._current_sel:     Optional[VariableSelection] = None
        self._numeric_vars:    list[str] = []
        self._exporter         = Exporter()
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(6)

        # ── Top bar: chart dropdown + (univariate) variable picker + buttons ──
        top_bar = QHBoxLayout()

        chart_label = QLabel("Chart:")
        chart_label.setStyleSheet(f"color: {GREY_500}; font-size: 12px;")
        top_bar.addWidget(chart_label)

        self.chart_combo = QComboBox()
        self.chart_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.chart_combo.currentIndexChanged.connect(self._render_selected)
        top_bar.addWidget(self.chart_combo, 1)

        # Variable picker — only shown for univariate tab when >1 numeric var
        self._var_picker_label = QLabel("Variable:")
        self._var_picker_label.setStyleSheet(f"color: {GREY_500}; font-size: 12px;")
        self._var_picker_label.setVisible(False)
        top_bar.addWidget(self._var_picker_label)

        self._var_picker = QComboBox()
        self._var_picker.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self._var_picker.setVisible(False)
        self._var_picker.currentIndexChanged.connect(self._render_selected)
        top_bar.addWidget(self._var_picker, 1)

        self.edit_btn = QPushButton("Quick Edit")
        self.edit_btn.setMinimumWidth(90)
        self.edit_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.edit_btn.setEnabled(False)
        self.edit_btn.clicked.connect(self._on_edit)
        top_bar.addWidget(self.edit_btn)

        self.export_btn = QPushButton("Export PNG")
        self.export_btn.setMinimumWidth(100)
        self.export_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.export_btn.setEnabled(False)
        self.export_btn.clicked.connect(self._on_export)
        top_bar.addWidget(self.export_btn)

        layout.addLayout(top_bar)

        # ── Matplotlib canvas ──────────────────────────────────────────────────
        self.fig    = Figure(figsize=(8, 5), dpi=100)
        self.canvas = FigureCanvasQTAgg(self.fig)
        self.canvas.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

        self.toolbar = NavigationToolbar2QT(self.canvas, self)
        self.toolbar.setVisible(False)

        layout.addWidget(self.toolbar)
        layout.addWidget(self.canvas, 1)

        # ── Placeholder (shown before data is loaded) ─────────────────────────
        dim_hints = {
            "univariate":  "Load a file and select an X-Axis variable.",
            "bivariate":   "Select X-Axis and Y-Axis variables to see bivariate charts.",
            "trivariate":  "Select X-Axis, Y-Axis, and a Z-Axis variable to see multivariate charts.",
        }
        self.placeholder = QLabel(dim_hints.get(self._dimensionality, "Select variables."))
        self.placeholder.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.placeholder.setWordWrap(True)
        self.placeholder.setStyleSheet(
            f"color: {GREY_400}; font-size: 14px; background: {GREY_50}; padding: 40px;"
        )
        self.placeholder.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        layout.addWidget(self.placeholder)

        self.canvas.setVisible(False)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_charts(
        self,
        df: pd.DataFrame,
        selection: VariableSelection,
        specs: list[ChartSpec],
        all_instances: dict[str, BaseChart],
        numeric_vars: list[str] | None = None,
    ) -> None:
        """Populate the chart dropdown and render the first (or previously selected) chart."""
        self._current_df  = df
        self._current_sel = selection
        self._chart_specs = specs
        self._chart_instances = all_instances
        self._numeric_vars = numeric_vars or []

        # ── Update variable picker (univariate only) ───────────────────────
        # Show picker whenever more than one variable is selected, regardless
        # of type — each variable has its own applicable univariate charts.
        show_picker = (
            self._dimensionality == "univariate" and len(self._numeric_vars) > 1
        )

        self._var_picker_label.setVisible(show_picker)
        self._var_picker.setVisible(show_picker)

        if show_picker:
            prev_var = self._var_picker.currentText()
            self._var_picker.blockSignals(True)
            self._var_picker.clear()
            self._var_picker.addItems(self._numeric_vars)
            # Restore previously chosen var if still present; otherwise prefer x_var
            if prev_var in self._numeric_vars:
                self._var_picker.setCurrentText(prev_var)
            elif selection.x_var in self._numeric_vars:
                self._var_picker.setCurrentText(selection.x_var)
            else:
                self._var_picker.setCurrentIndex(0)
            self._var_picker.blockSignals(False)

        # ── Update chart selector combo ────────────────────────────────────
        prev_id = self.chart_combo.currentData()

        self.chart_combo.blockSignals(True)
        self.chart_combo.clear()
        for spec in specs:
            self.chart_combo.addItem(spec.name, userData=spec.chart_id)
        self.chart_combo.blockSignals(False)

        # Restore previous selection if it's still applicable
        restored = False
        if prev_id:
            for i in range(self.chart_combo.count()):
                if self.chart_combo.itemData(i) == prev_id:
                    self.chart_combo.setCurrentIndex(i)
                    restored = True
                    break

        if not restored:
            self.chart_combo.setCurrentIndex(0)

        self._render_selected()

    def clear(self) -> None:
        self._current_df  = None
        self._current_sel = None
        self._chart_specs = []
        self._numeric_vars = []
        self.chart_combo.blockSignals(True)
        self.chart_combo.clear()
        self.chart_combo.blockSignals(False)
        self._var_picker.setVisible(False)
        self._var_picker_label.setVisible(False)
        self.fig.clear()
        self.canvas.draw()
        self.canvas.setVisible(False)
        self.placeholder.setVisible(True)
        self.toolbar.setVisible(False)
        self.edit_btn.setEnabled(False)
        self.export_btn.setEnabled(False)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _update_chart_combo(self, specs: list[ChartSpec]) -> None:
        """
        Repopulate the chart dropdown with *specs* (without triggering a render).

        Tries to keep the previously-selected chart if it still applies; falls
        back to the first item in the new list.  Updates self._chart_specs so
        that the change-detection in _render_selected() stays consistent.
        """
        prev_id = self.chart_combo.currentData()
        self.chart_combo.blockSignals(True)
        self.chart_combo.clear()
        for spec in specs:
            self.chart_combo.addItem(spec.name, userData=spec.chart_id)
        restored = False
        if prev_id:
            for i in range(self.chart_combo.count()):
                if self.chart_combo.itemData(i) == prev_id:
                    self.chart_combo.setCurrentIndex(i)
                    restored = True
                    break
        if not restored:
            self.chart_combo.setCurrentIndex(0)
        self.chart_combo.blockSignals(False)
        self._chart_specs = specs

    def _render_selected(self) -> None:
        if self._current_df is None or self._current_sel is None:
            return

        # ── Univariate: re-filter chart list when picked variable type changes ─
        # The initial chart list is seeded from x_type(); when the user picks a
        # different variable in the variable picker, recompute the applicable
        # charts for *that* variable's type so the dropdown stays correct.
        sel = self._current_sel
        if self._dimensionality == "univariate" and self._var_picker.isVisible():
            chosen = self._var_picker.currentText()
            if chosen:
                var_type    = sel.var_types.get(chosen)
                needed_specs = ChartSelector.univariate_specs(var_type)
                if needed_specs != self._chart_specs:
                    self._update_chart_combo(needed_specs)
                # Substitute x_var so charts render the chosen variable
                if chosen != sel.x_var:
                    sel = dc_replace(sel, x_var=chosen)

        chart_id = self.chart_combo.currentData()
        if not chart_id:
            return

        # Lazily instantiate chart
        if chart_id not in self._chart_instances:
            cls = CHART_REGISTRY.get(chart_id)
            if cls is None:
                return
            self._chart_instances[chart_id] = cls()

        chart = self._chart_instances[chart_id]

        try:
            chart.render(self._current_df, sel, self.fig)
        except Exception as exc:
            self.fig.clear()
            ax = self.fig.add_subplot(111)
            ax.text(0.5, 0.5, f"Could not render chart:\n{exc}",
                    ha='center', va='center', transform=ax.transAxes,
                    color="#94A3B8", fontsize=11, wrap=True)
            self.fig.tight_layout()

        self.canvas.draw()
        self.canvas.setVisible(True)
        self.placeholder.setVisible(False)
        self.toolbar.setVisible(True)
        self.edit_btn.setEnabled(True)
        self.export_btn.setEnabled(True)

    def _on_edit(self) -> None:
        chart_id = self.chart_combo.currentData()
        if not chart_id or chart_id not in self._chart_instances:
            return
        chart = self._chart_instances[chart_id]
        dlg   = ChartEditDialog(chart, parent=self)
        if dlg.exec():
            chart.update_edit_options(dlg.get_updated_options())
            self._render_selected()

    def _on_export(self) -> None:
        chart_id = self.chart_combo.currentData()
        if not chart_id:
            return
        path, _ = QFileDialog.getSaveFileName(
            self, "Export chart as PNG", f"{chart_id}.png",
            "PNG image (*.png)"
        )
        if path:
            try:
                self._exporter.export_figure(self.fig, path, dpi=300)
                QMessageBox.information(self, "Exported",
                                        f"Saved 300 DPI PNG to:\n{path}")
            except Exception as exc:
                QMessageBox.critical(self, "Export error", str(exc))


# ── ChartDashboard ─────────────────────────────────────────────────────────────

class ChartDashboard(QWidget):
    """
    Three-tab chart dashboard (Univariate / Bivariate / Trivariate).

    Owns all chart instances — they persist across variable changes so that
    edit options are preserved.
    """

    _DIMS = ["univariate", "bivariate", "trivariate"]
    _TAB_LABELS = {
        "univariate":  "Univariate",
        "bivariate":   "Bivariate",
        "trivariate":  "Multivariate",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        # Shared dict of all instantiated chart objects (keyed by chart_id)
        self._chart_instances: dict[str, BaseChart] = {}
        self._build_ui()

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        self.tabs = QTabWidget()
        self.panes: dict[str, ChartTabPane] = {}

        for dim in self._DIMS:
            pane = ChartTabPane(dim, parent=self)
            self.panes[dim] = pane
            self.tabs.addTab(pane, self._TAB_LABELS[dim])

        self._set_tabs_enabled(False, False, False)
        self.tabs.setCurrentIndex(0)   # always start on Univariate
        layout.addWidget(self.tabs)

        # Fix macOS native-view bleed-through: explicitly manage canvas
        # visibility when the user switches tabs (NSView doesn't auto-hide).
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ── Public API ─────────────────────────────────────────────────────────────

    def set_data(
        self,
        df: pd.DataFrame,
        selection: VariableSelection,
        applicable: dict[str, list[ChartSpec]],
    ) -> None:
        """Update all tabs with the new data and applicable chart lists."""
        has_any = False
        first_active_dim = None

        # All selected variables — passed to the univariate pane for the
        # variable picker (which shows every selected column).
        all_selected_vars = [
            col
            for col in (selection.x_var, selection.y_var, selection.group_var)
            if col is not None
        ]

        for i, dim in enumerate(self._DIMS):
            specs = applicable.get(dim, [])
            has_charts = len(specs) > 0
            self.tabs.setTabEnabled(i, has_charts)

            if has_charts:
                extra = {"numeric_vars": all_selected_vars} if dim == "univariate" else {}
                self.panes[dim].set_charts(df, selection, specs, self._chart_instances, **extra)
                has_any = True
                if first_active_dim is None:
                    first_active_dim = dim
            else:
                self.panes[dim].clear()

        # Switch to first tab that has content
        if first_active_dim:
            idx = self._DIMS.index(first_active_dim)
            current_idx = self.tabs.currentIndex()
            # Only switch if current tab is disabled
            if not self.tabs.isTabEnabled(current_idx):
                self.tabs.setCurrentIndex(idx)

        # Explicitly hide inactive canvases — required on macOS where the
        # native NSView backing FigureCanvasQTAgg doesn't honour parent-level
        # visibility changes made by QTabWidget when switching pages.
        self._sync_canvas_visibility()

    def clear(self) -> None:
        """Clear all tab panes (called when a new file is loaded)."""
        for pane in self.panes.values():
            pane.clear()
        self._set_tabs_enabled(False, False, False)

    # ── Internal ───────────────────────────────────────────────────────────────

    def _on_tab_changed(self, idx: int) -> None:
        """
        Called whenever the active tab changes.

        On macOS, FigureCanvasQTAgg is backed by a native NSView that does not
        automatically hide when its Qt parent page is hidden.  We work around
        this by explicitly hiding every canvas that is NOT in the active tab
        and, if the newly active tab already has a rendered chart, refreshing
        its canvas so it fills the newly visible area cleanly.
        """
        self._sync_canvas_visibility()
        # Repaint the active pane so the canvas fills the full tab area
        active_dim = self._DIMS[idx] if 0 <= idx < len(self._DIMS) else None
        if active_dim:
            pane = self.panes[active_dim]
            if pane._current_df is not None and pane.canvas.isVisible():
                pane.canvas.draw_idle()

    def _sync_canvas_visibility(self) -> None:
        """Hide canvases of every inactive tab; show the active tab's canvas."""
        active_idx = self.tabs.currentIndex()
        for i, dim in enumerate(self._DIMS):
            pane = self.panes[dim]
            if i == active_idx:
                # Only show canvas when there is actually rendered content
                if pane._current_df is not None and not pane.placeholder.isVisible():
                    pane.canvas.setVisible(True)
                    pane.toolbar.setVisible(True)
            else:
                # Force-hide the native canvas widget to prevent macOS bleed-through
                pane.canvas.setVisible(False)
                pane.toolbar.setVisible(False)

    def _set_tabs_enabled(self, uni: bool, bi: bool, tri: bool) -> None:
        flags = [uni, bi, tri]
        for i, flag in enumerate(flags):
            self.tabs.setTabEnabled(i, flag)
