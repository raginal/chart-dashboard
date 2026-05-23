"""
Generic chart edit dialog.

Dynamically builds form widgets from a chart's edit_options schema dict.
Schema format per option key:
    {
        "label":   str,
        "type":    "text" | "bool" | "choice",
        "default": <any>,
        "choices": [str, ...]   # only for type == "choice"
    }

Updated values are accessible via get_updated_options() → dict[str, value].
"""
from __future__ import annotations
from typing import TYPE_CHECKING

from PyQt6.QtWidgets import (
    QDialog, QVBoxLayout, QHBoxLayout, QLabel, QLineEdit,
    QCheckBox, QComboBox, QPushButton, QFormLayout, QFrame,
)
from PyQt6.QtCore import Qt

if TYPE_CHECKING:
    from charts.base import BaseChart


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
        layout.setSpacing(12)

        form = QFormLayout()
        form.setFieldGrowthPolicy(QFormLayout.FieldGrowthPolicy.ExpandingFieldsGrow)
        form.setLabelAlignment(Qt.AlignmentFlag.AlignRight)

        for key, schema in self._options.items():
            label_text = schema.get("label", key)
            opt_type   = schema.get("type", "text")
            current    = schema.get("value", schema.get("default", ""))

            if opt_type == "bool":
                widget = QCheckBox()
                widget.setChecked(bool(current))
                self._widgets[key] = widget
                form.addRow(label_text + ":", widget)

            elif opt_type == "choice":
                widget = QComboBox()
                choices = schema.get("choices", [])
                widget.addItems([str(c) for c in choices])
                if str(current) in choices:
                    widget.setCurrentText(str(current))
                self._widgets[key] = widget
                form.addRow(label_text + ":", widget)

            else:  # "text"
                widget = QLineEdit()
                widget.setText(str(current) if current is not None else "")
                widget.setPlaceholderText(f"Default: {schema.get('default', '')}")
                self._widgets[key] = widget
                form.addRow(label_text + ":", widget)

        layout.addLayout(form)

        # ── Separator ──────────────────────────────────────────────────────────
        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setFrameShadow(QFrame.Shadow.Plain)
        layout.addWidget(sep)

        # ── Buttons ────────────────────────────────────────────────────────────
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
