"""
Per-variable data transformations.

Each transformation is applied to a pandas Series before charting.
The original DataFrame is never mutated — a working copy is returned.
"""

import pandas as pd
import numpy as np
from enum import Enum


class TransformType(Enum):
    NONE        = "None"
    LN          = "Natural Log"
    PCT_CHANGE  = "Percent Change"
    FIRST_DIFF  = "First Difference"
    LAG_1       = "Lag 1 Period"
    LAG_2       = "Lag 2 Periods"
    LAG_3       = "Lag 3 Periods"


class VariableTransformer:
    """
    Applies TransformType transformations to individual Series or to all
    selected columns in a DataFrame.

    Notes
    -----
    - Transforms that introduce NaN (log of non-positive, lag/diff at edges)
      preserve index alignment — no rows are dropped.
    - The caller (MainWindow) passes only the transform dict for variables
      that are actually selected; unselected columns are untouched.
    """

    def apply(self, series: pd.Series, transform: TransformType) -> pd.Series:
        """Apply a single transform to a Series.  Returns a new Series."""
        if transform == TransformType.NONE:
            return series.copy()

        if transform == TransformType.LN:
            numeric = pd.to_numeric(series, errors='coerce')
            return np.log(numeric.where(numeric > 0))

        if transform == TransformType.PCT_CHANGE:
            numeric = pd.to_numeric(series, errors='coerce')
            return numeric.pct_change() * 100

        if transform == TransformType.FIRST_DIFF:
            numeric = pd.to_numeric(series, errors='coerce')
            return numeric.diff()

        if transform == TransformType.LAG_1:
            return series.shift(1)

        if transform == TransformType.LAG_2:
            return series.shift(2)

        if transform == TransformType.LAG_3:
            return series.shift(3)

        return series.copy()

    def apply_all(
        self,
        df: pd.DataFrame,
        transforms: dict[str, TransformType],
    ) -> pd.DataFrame:
        """
        Return a copy of df with the specified transforms applied column-wise.

        Parameters
        ----------
        df         : Working DataFrame (already filtered/recoded by consolidator).
        transforms : {column_name: TransformType}. Only columns present in df
                     AND in this dict are transformed.
        """
        df_out = df.copy()
        for col, transform in transforms.items():
            if col in df_out.columns and transform != TransformType.NONE:
                df_out[col] = self.apply(df_out[col], transform)
        return df_out

    @staticmethod
    def axis_label(col_name: str, transform: TransformType) -> str:
        """Return a human-readable axis label with the transform suffix appended."""
        if transform == TransformType.NONE:
            return col_name
        return f"{col_name} ({transform.value})"
