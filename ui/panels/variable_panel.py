"""
Variable selection panel — left side of the chartBuilder window.

Contains three VariableSlot widgets (X-Axis, Y-Axis, Z-Axis), each with a
variable dropdown, type selector, transform menu, and clean button.

The Z-Axis slot replaces the former "Group By", "Colour By", and "2nd X-Axis"
slots.  It acts as the single third-variable input: used for faceting (Small
Multiples, Faceted Histogram), Sankey sections, scatter-plot colouring, and
any other role previously spread across those three slots.

Emits selection_changed(VariableSelection) via a 300 ms debounce after any change.

Transform availability by variable type
---------------------------------------
  Nominal / Ordinal / Location  → None only (no transforms make sense)
  Date                          → None, Lag 1–3 (date shifting is meaningful)
  Interval / Ratio              → all transforms
"""
from __future__ import annotations
from typing import Optional

import pandas as pd
from PyQt6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QLabel, QComboBox,
    QPushButton, QGroupBox, QMenu, QScrollArea, QFrame, QSizePolicy,
)
from PyQt6.QtCore import pyqtSignal, QTimer, Qt
from PyQt6.QtGui import QAction

from core.variable_classifier import VariableType
from core.transformer import TransformType
from core.chart_config import VariableSelection
from core.consolidator import ResponseConsolidator
from ui.dialogs.consolidate_dialog import ConsolidateDialog
from ui.palette import PRIMARY, GREY_200, GREY_500

DEBOUNCE_MS = 300

# ── Transform availability by variable type ───────────────────────────────────

_CATEGORICAL_TYPES = (VariableType.NOMINAL, VariableType.ORDINAL, VariableType.LOCATION)

_TRANSFORMS_FOR: dict[VariableType, list[TransformType]] = {
    VariableType.NOMINAL:  [TransformType.NONE],
    VariableType.ORDINAL:  [TransformType.NONE],
    VariableType.LOCATION: [TransformType.NONE],
    VariableType.DATE: [
        TransformType.NONE,
        TransformType.LAG_1,
        TransformType.LAG_2,
        TransformType.LAG_3,
    ],
    VariableType.INTERVAL: list(TransformType),   # all
}


def _available_transforms(vtype: VariableType | None) -> list[TransformType]:
    """Return the list of TransformType values valid for *vtype*."""
    if vtype is None:
        return [TransformType.NONE]
    return _TRANSFORMS_FOR.get(vtype, list(TransformType))


class VariableSlot(QWidget):
    """
    One labelled variable slot row:
      [Role label] [Variable dropdown ──────] [Type combo] [▼ Transform] [Clean]
    """
    changed = pyqtSignal()
    consolidate_clicked = pyqtSignal(str)   # column name

    _SLOT_TIPS = {
        "X-Axis": "Independent variable — shown on the X-axis",
        "Y-Axis": "Dependent variable — shown on the Y-axis",
        "Z-Axis": (
            "Third variable — used for grouping/faceting (Small Multiples, "
            "Faceted Histogram), Sankey flow sections, and scatter-plot colouring"
        ),
    }

    def __init__(self, slot_name: str, required: bool = False, parent=None):
        super().__init__(parent)
        self._slot_name = slot_name
        self._required  = required
        self._df: Optional[pd.DataFrame] = None
        self._auto_types: dict[str, VariableType] = {}
        self._transform = TransformType.NONE
        self._consolidator = ResponseConsolidator()
        self._build_ui()

    _LABEL_W = 80   # px — fixed label column width
    _INDENT  = _LABEL_W + 6

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 3, 0, 3)
        outer.setSpacing(4)

        # ── Row 1: label + variable dropdown ────────────────────────────────
        row1 = QHBoxLayout()
        row1.setSpacing(6)
        row1.setContentsMargins(0, 0, 0, 0)

        req_marker = " *" if self._required else ""
        lbl = QLabel(f"{self._slot_name}{req_marker}:")
        lbl.setFixedWidth(self._LABEL_W)
        lbl.setAlignment(Qt.AlignmentFlag.AlignRight | Qt.AlignmentFlag.AlignVCenter)
        lbl.setToolTip(self._SLOT_TIPS.get(self._slot_name, ""))
        lbl.setStyleSheet(f"color: {GREY_500}; font-size: 11px; font-weight: 600;")
        row1.addWidget(lbl)

        self.var_combo = QComboBox()
        self.var_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.var_combo.setToolTip("Select a column")
        self.var_combo.currentIndexChanged.connect(self._on_var_changed)
        row1.addWidget(self.var_combo, 1)

        outer.addLayout(row1)

        # ── Row 2: indent + type + transform + clean ─────────────────────────
        row2 = QHBoxLayout()
        row2.setSpacing(6)
        row2.setContentsMargins(0, 0, 0, 0)
        row2.addSpacing(self._INDENT)

        self.type_combo = QComboBox()
        self.type_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.type_combo.addItems([vt.value for vt in VariableType])
        self.type_combo.setToolTip("Variable type (auto-detected; editable)")
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)
        self.type_combo.setEnabled(False)
        row2.addWidget(self.type_combo, 1)

        self.transform_btn = QPushButton("▼ None")
        self.transform_btn.setMinimumWidth(82)
        self.transform_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.transform_btn.setToolTip("Apply a mathematical transformation to this variable")
        self.transform_btn.clicked.connect(self._show_transform_menu)
        self.transform_btn.setEnabled(False)
        row2.addWidget(self.transform_btn)

        self.clean_btn = QPushButton("Clean")
        self.clean_btn.setMinimumWidth(52)
        self.clean_btn.setSizePolicy(QSizePolicy.Policy.Preferred, QSizePolicy.Policy.Fixed)
        self.clean_btn.setToolTip("Filter or recode values for this variable")
        self.clean_btn.clicked.connect(self._on_clean_clicked)
        self.clean_btn.setEnabled(False)
        row2.addWidget(self.clean_btn)

        outer.addLayout(row2)

    # ── Public API ────────────────────────────────────────────────────────────

    def populate(self, columns: list[str], auto_types: dict[str, VariableType]) -> None:
        self._auto_types = auto_types
        self.var_combo.blockSignals(True)
        current = self.var_combo.currentText()
        self.var_combo.clear()
        self.var_combo.addItem("(none)")
        self.var_combo.addItems(columns)
        if current in columns:
            self.var_combo.setCurrentText(current)
        self.var_combo.blockSignals(False)
        self._on_var_changed()

    def get_variable(self) -> Optional[str]:
        txt = self.var_combo.currentText()
        return txt if txt != "(none)" else None

    def get_type(self) -> Optional[VariableType]:
        txt = self.type_combo.currentText()
        for vt in VariableType:
            if vt.value == txt:
                return vt
        return None

    def get_transform(self) -> TransformType:
        return self._transform

    def get_consolidation(self) -> Optional[dict]:
        col = self.get_variable()
        if col and self._consolidator.has_mapping(col):
            return self._consolidator.get_mapping(col)
        return None

    def clear(self) -> None:
        self.var_combo.blockSignals(True)
        self.var_combo.clear()
        self.var_combo.addItem("(none)")
        self.var_combo.blockSignals(False)
        self.type_combo.setEnabled(False)
        self.transform_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self._transform = TransformType.NONE
        self.transform_btn.setText("▼ None")

    def reset_to_none(self) -> None:
        """Reset selection to '(none)' without clearing the column list."""
        self.var_combo.blockSignals(True)
        self.var_combo.setCurrentIndex(0)
        self.var_combo.blockSignals(False)
        self._transform = TransformType.NONE
        self.transform_btn.setText("▼ None")
        self.type_combo.setEnabled(False)
        self.transform_btn.setEnabled(False)
        self.clean_btn.setEnabled(False)
        self.changed.emit()

    def set_dataframe(self, df: pd.DataFrame) -> None:
        self._df = df

    # ── Internal slots ────────────────────────────────────────────────────────

    def _on_var_changed(self) -> None:
        col     = self.get_variable()
        enabled = col is not None
        self.type_combo.setEnabled(enabled)
        self.transform_btn.setEnabled(enabled)
        self.clean_btn.setEnabled(enabled)

        if enabled and col in self._auto_types:
            vtype = self._auto_types[col]
            self.type_combo.blockSignals(True)
            self.type_combo.setCurrentText(vtype.value)
            self.type_combo.blockSignals(False)

        # Reset transform whenever the variable changes
        self._set_transform(TransformType.NONE, emit=False)
        self._update_transform_btn_tooltip()
        self.changed.emit()

    def _on_type_changed(self) -> None:
        """
        Called when the user manually changes the type selector.

        If the currently-active transform is not valid for the new type,
        silently reset it to None before emitting changed.
        """
        available = _available_transforms(self.get_type())
        if self._transform not in available:
            self._set_transform(TransformType.NONE, emit=False)
        self._update_transform_btn_tooltip()
        self.changed.emit()

    def _show_transform_menu(self) -> None:
        available = _available_transforms(self.get_type())
        menu = QMenu(self)
        for tt in available:
            action = QAction(tt.value, self)
            action.setCheckable(True)
            action.setChecked(tt == self._transform)
            action.triggered.connect(lambda checked, t=tt: self._set_transform(t))
            menu.addAction(action)
        menu.exec(self.transform_btn.mapToGlobal(
            self.transform_btn.rect().bottomLeft()
        ))

    def _set_transform(self, transform: TransformType, emit: bool = True) -> None:
        self._transform = transform
        short = transform.value.split()[0] if transform != TransformType.NONE else "None"
        self.transform_btn.setText(f"▼ {short}")
        if emit:
            self.changed.emit()

    def _update_transform_btn_tooltip(self) -> None:
        """Show a tooltip explaining which transforms are available for the current type."""
        vtype = self.get_type()
        if vtype in _CATEGORICAL_TYPES:
            tip = "No transforms available for categorical / location variables"
        elif vtype == VariableType.DATE:
            tip = "Available transforms: Lag 1–3 Periods"
        else:
            tip = "Apply a mathematical transformation to this variable"
        self.transform_btn.setToolTip(tip)

    def _on_clean_clicked(self) -> None:
        col = self.get_variable()
        if not col or self._df is None:
            return
        values = self._df[col].dropna().unique().tolist()
        existing = self._consolidator.get_mapping(col)
        dlg = ConsolidateDialog(col, values, existing_mapping=existing, parent=self)
        if dlg.exec():
            mapping = dlg.get_mapping()
            is_identity = all(
                v is not None and str(v) == str(k)
                for k, v in mapping.items()
            )
            if is_identity:
                self._consolidator.remove_mapping(col)
            else:
                self._consolidator.set_mapping(col, mapping)
            self.changed.emit()


# ── VariablePanel ─────────────────────────────────────────────────────────────

class VariablePanel(QWidget):
    """
    Full left-side variable configuration panel.

    Contains three VariableSlot widgets (X-Axis, Y-Axis, Z-Axis) and emits
    selection_changed(VariableSelection) 300 ms after any change.
    """
    selection_changed = pyqtSignal(object)   # VariableSelection

    _SLOTS: list[tuple[str, bool]] = [
        ("X-Axis", True),    # (slot_name, required)
        ("Y-Axis", False),
        ("Z-Axis", False),
    ]

    def __init__(self, parent=None):
        super().__init__(parent)
        self._df: Optional[pd.DataFrame] = None
        self._debounce = QTimer(self)
        self._debounce.setSingleShot(True)
        self._debounce.setInterval(DEBOUNCE_MS)
        self._debounce.timeout.connect(self._emit_selection)
        self._build_ui()

    def _build_ui(self) -> None:
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        group = QGroupBox("Variables")
        g_layout = QVBoxLayout(group)
        g_layout.setSpacing(4)

        # Top bar: instruction label + Clear All button
        top_bar = QHBoxLayout()
        top_bar.setContentsMargins(0, 0, 0, 0)

        instr = QLabel("Select variables below. Charts update automatically.")
        instr.setWordWrap(True)
        instr.setStyleSheet(f"color: {GREY_500}; font-size: 11px; padding: 2px 0 6px 0;")
        top_bar.addWidget(instr, 1)

        self._clear_all_btn = QPushButton("Clear All")
        self._clear_all_btn.setMinimumWidth(70)
        self._clear_all_btn.setMaximumHeight(24)
        self._clear_all_btn.setStyleSheet("font-size: 11px; padding: 2px 8px;")
        self._clear_all_btn.setToolTip("Reset all variable selections and transforms to None")
        self._clear_all_btn.clicked.connect(self.clear_all)
        top_bar.addWidget(self._clear_all_btn)

        g_layout.addLayout(top_bar)

        sep = QFrame()
        sep.setFrameShape(QFrame.Shape.HLine)
        sep.setStyleSheet(f"color: {GREY_200};")
        g_layout.addWidget(sep)

        # Create the 3 slots
        self.slots: dict[str, VariableSlot] = {}
        slot_keys = ["x", "y", "group"]
        for key, (slot_name, required) in zip(slot_keys, self._SLOTS):
            slot = VariableSlot(slot_name, required=required)
            slot.changed.connect(self._on_any_change)
            self.slots[key] = slot
            g_layout.addWidget(slot)
            if key != "group":
                line = QFrame()
                line.setFrameShape(QFrame.Shape.HLine)
                line.setStyleSheet(f"color: {GREY_200};")
                g_layout.addWidget(line)

        outer.addWidget(group)
        outer.addStretch()

    # ── Public API ────────────────────────────────────────────────────────────

    def set_data(self, df: pd.DataFrame, auto_types: dict[str, VariableType]) -> None:
        self._df = df
        cols = list(df.columns)
        for slot in self.slots.values():
            slot.set_dataframe(df)
            slot.populate(cols, auto_types)

    def clear(self) -> None:
        self._df = None
        for slot in self.slots.values():
            slot.clear()

    def clear_all(self) -> None:
        """Reset every slot to '(none)' and all transforms to None."""
        self._debounce.stop()
        for slot in self.slots.values():
            slot.reset_to_none()
        self._debounce.start()

    # ── Internal ──────────────────────────────────────────────────────────────

    def _on_any_change(self) -> None:
        self._debounce.start()

    def _emit_selection(self) -> None:
        x_var     = self.slots["x"].get_variable()
        y_var     = self.slots["y"].get_variable()
        group_var = self.slots["group"].get_variable()

        var_types: dict[str, VariableType] = {}
        for slot in self.slots.values():
            col = slot.get_variable()
            vt  = slot.get_type()
            if col and vt:
                var_types[col] = vt

        transforms: dict[str, TransformType] = {}
        for slot in self.slots.values():
            col = slot.get_variable()
            t   = slot.get_transform()
            if col and t != TransformType.NONE:
                transforms[col] = t

        consolidations: dict[str, dict] = {}
        for slot in self.slots.values():
            col = slot.get_variable()
            m   = slot.get_consolidation()
            if col and m:
                consolidations[col] = m

        selection = VariableSelection(
            x_var=x_var,
            y_var=y_var,
            group_var=group_var,
            var_types=var_types,
            transforms=transforms,
            consolidations=consolidations,
        )
        self.selection_changed.emit(selection)
