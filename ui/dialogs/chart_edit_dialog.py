"""
Generic chart edit dialog.

Dynamically builds form widgets from a chart's edit_options schema dict.
Schema format per option key:
    {
        "label":   str,
        "type":    "text" | "bool" | "choice",
        "default": <any>,
        "choices": [str, ...]   # only for type == "choice"
        "group":   "title" | "axes" | "color" | "other"  # optional override
    }

Options are displayed in four groups separated by subtle horizontal lines:
  1. Title  — chart title + bold/alignment toggles (keys starting with "title")
  2. Axes   — axis labels and axis-behaviour controls
  3. Color  — colour / palette selectors (keys containing "color" or "palette")
  4. Other  — layout, bins, chart type, feature toggles

A schema entry may carry ``"group": "<name>"`` to override the heuristic.
See ``_classify_group()`` for the full logic.

Updated values are accessible via get_updated_options() → dict[str, value].
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLineEdit,
    QCheckBox, QComboBox, QPushButton, QFormLayout, QFrame,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from charts.base import BaseChart

# Canonical display order for the four groups
_GROUP_ORDER = ["title", "axes", "color", "other"]


def _classify_group(key: str, schema: dict) -> str:
    """
    Assign an edit-option key to one of four display groups.

    Priority:
      1. Explicit ``"group"`` field in *schema* — use it directly.
      2. Key starts with ``"title"``         → ``"title"``
      3. Key contains ``"color"`` or ``"palette"`` → ``"color"``
      4. Key ends with ``"_label"`` or is in the axis-behaviour set
         (``rotate_x``, ``sort_x``, ``shared_x``, ``shared_axes``)  → ``"axes"``
      5. Everything else                      → ``"other"``

    When naming new options, following these conventions means the grouping
    works automatically without adding an explicit ``"group"`` key.
    """
    if "group" in schema:
        g = schema["group"]
        return g if g in _GROUP_ORDER else "other"
    if key.startswith("title"):
        return "title"
    if "color" in key or "palette" in key:
        return "color"
    if key.endswith("_label") or key in {
        "rotate_x", "sort_x", "shared_x", "shared_axes",
    }:
        return "axes"
    return "other"


class ChartEditDialog(QDialog):
    """Modal dialog for editing chart-specific options."""

    def __init__(self, chart: "BaseChart", parent=None):
        super().__init__(parent)
        self.setWindowTitle(f"Edit Chart — {chart.DISPLAY_NAME}")
        self.setMinimumWidth(380)

        self._chart   = chart
        self._options = chart.get_edit_options()
        self._widgets: dict[str, QCheckBox | QLineEdit | QComboBox] = {}

        layout = QVBoxLayout(self)
        layout.setSpacing(8)
        layout.setContentsMargins(12, 12, 12, 12)

        # ── Bucket options into groups (preserving declaration order) ─────────
        grouped: dict[str, list[tuple[str, dict]]] = {g: [] for g in _GROUP_ORDER}
        for key, schema in self._options.items():
            group = _classify_group(key, schema)
            grouped[group].append((key, schema))

        # ── Render each non-empty group, separated by subtle dividers ─────────
        first_visible = True
        for group_name in _GROUP_ORDER:
            items = grouped[group_name]
            if not items:
                continue

            if not first_visible:
                self._add_group_separator(layout)
            first_visible = False

            form = QFormLayout()
            form.setFieldGrowthPolicy(
                QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow
            )
            form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)
            form.setVerticalSpacing(6)
            form.setHorizontalSpacing(10)

            for key, schema in items:
                widget = self._make_widget(key, schema)
                self._widgets[key] = widget
                form.addRow(schema.get("label", key) + ":", widget)

            layout.addLayout(form)

        # ── Separator before action buttons ───────────────────────────────────
        layout.addSpacing(4)
        btn_sep = QFrame()
        btn_sep.setFrameShape(QFrame.Shape.HLine)
        btn_sep.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(btn_sep)

        # ── Action buttons ────────────────────────────────────────────────────
        btn_row = QHBoxLayout()
        btn_row.addStretch()
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        apply_btn  = QPushButton("Apply")
        apply_btn.setObjectName("primary_btn")
        apply_btn.setDefault(True)
        apply_btn.clicked.connect(self.accept)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

    # ── Internal helpers ──────────────────────────────────────────────────────

    @staticmethod
    def _add_group_separator(layout: QVBoxLayout) -> None:
        """Insert a subtle horizontal rule between option groups."""
        layout.addSpacing(4)
        line = QFrame()
        line.setFrameShape(QFrame.Shape.HLine)
        line.setFrameShadow(QFrame.Shadow.Plain)
        # Use GREY_200 (#E2E8F0) to match the app's divider colour
        line.setStyleSheet("QFrame { color: #E2E8F0; }")
        layout.addWidget(line)
        layout.addSpacing(4)

    @staticmethod
    def _make_widget(key: str, schema: dict) -> QCheckBox | QLineEdit | QComboBox:
        """Build and return the appropriate input widget for one edit option."""
        opt_type = schema.get("type", "text")
        current  = schema.get("value", schema.get("default", ""))

        if opt_type == "bool":
            widget = QCheckBox()
            widget.setChecked(bool(current))
            return widget

        if opt_type == "choice":
            widget = QComboBox()
            choices = schema.get("choices", [])
            widget.addItems([str(c) for c in choices])
            if str(current) in [str(c) for c in choices]:
                widget.setCurrentText(str(current))
            return widget

        # "text" (default)
        widget = QLineEdit()
        widget.setText(str(current) if current is not None else "")
        widget.setPlaceholderText(f"Default: {schema.get('default', '')}")
        return widget

    def get_updated_options(self) -> dict:
        """Return {key: new_value} for all editable options."""
        result = {}
        for key, widget in self._widgets.items():
            if isinstance(widget, QCheckBox):
                result[key] = widget.isChecked()
            elif isinstance(widget, QComboBox):
                result[key] = widget.currentText()
            else:
                result[key] = widget.text()
        return result
