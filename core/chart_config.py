"""
Shared dataclasses for the chartBuilder data pipeline.

These dataclasses are the primary data transfer objects between the UI layer
and the core/chart layers.  All fields are primitives or enums so the
VariableSelection can be serialised to/from a plain dict in the future
(e.g. for save/restore sessions or linking with crosstabs).
"""

from __future__ import annotations
from dataclasses import dataclass, field
from typing import Optional

from core.variable_classifier import VariableType
from core.transformer import TransformType


@dataclass
class VariableSelection:
    """
    Captures the full user variable configuration from the left panel.

    Slot semantics
    --------------
    x_var     : Independent variable / X-Axis (required for any chart)
    y_var     : Dependent variable / Y-Axis
    group_var : Z-Axis variable — used for faceting, flow sections,
                scatter colouring, grouping, and any other third-variable role.

    var_types      : {column_name: VariableType} — may include overrides set by user
    transforms     : {column_name: TransformType} — per-variable transformation
    consolidations : {column_name: {orig_val: new_group_name | None}} — from ConsolidateDialog
    """
    x_var:     Optional[str] = None
    y_var:     Optional[str] = None
    group_var: Optional[str] = None

    var_types:      dict[str, VariableType] = field(default_factory=dict)
    transforms:     dict[str, TransformType] = field(default_factory=dict)
    consolidations: dict[str, dict]          = field(default_factory=dict)

    # ── Convenience helpers ───────────────────────────────────────────────────

    def selected_vars(self) -> list[str]:
        """Return a list of all non-None variable names in slot order."""
        return [
            v for v in (self.x_var, self.y_var, self.group_var)
            if v is not None
        ]

    def has_trivariate(self) -> bool:
        """True if x, y, and group_var are all selected."""
        return (
            self.x_var     is not None
            and self.y_var     is not None
            and self.group_var is not None
        )

    def has_bivariate(self) -> bool:
        """True if x and y are both selected."""
        return self.x_var is not None and self.y_var is not None

    def x_type(self) -> Optional[VariableType]:
        return self.var_types.get(self.x_var) if self.x_var else None

    def y_type(self) -> Optional[VariableType]:
        return self.var_types.get(self.y_var) if self.y_var else None

    def group_type(self) -> Optional[VariableType]:
        return self.var_types.get(self.group_var) if self.group_var else None

    def x_transform(self) -> TransformType:
        return self.transforms.get(self.x_var, TransformType.NONE) if self.x_var else TransformType.NONE

    def y_transform(self) -> TransformType:
        return self.transforms.get(self.y_var, TransformType.NONE) if self.y_var else TransformType.NONE


@dataclass
class ChartSpec:
    """
    Describes one available chart type for a given variable selection.

    chart_id       : Matches BaseChart.CHART_ID in the registry.
    dimensionality : "univariate" | "bivariate" | "trivariate"
    name           : Human-readable display name shown in the UI dropdown.
    """
    chart_id:       str
    dimensionality: str
    name:           str
