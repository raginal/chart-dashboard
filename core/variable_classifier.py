"""
Variable type classifier for chartBuilder.

Extends the crosstabs classifier by adding DATE and LOCATION variable types.
The analyst can always override the auto-detected type via the UI.
"""

import pandas as pd
import numpy as np
from enum import Enum


class VariableType(Enum):
    NOMINAL  = "Nominal"
    ORDINAL  = "Ordinal"
    INTERVAL = "Interval/Ratio"
    DATE     = "Date"
    LOCATION = "Location"


# ── US geography reference sets ───────────────────────────────────────────────

US_STATE_ABBREVS: frozenset[str] = frozenset({
    'AL', 'AK', 'AZ', 'AR', 'CA', 'CO', 'CT', 'DE', 'FL', 'GA',
    'HI', 'ID', 'IL', 'IN', 'IA', 'KS', 'KY', 'LA', 'ME', 'MD',
    'MA', 'MI', 'MN', 'MS', 'MO', 'MT', 'NE', 'NV', 'NH', 'NJ',
    'NM', 'NY', 'NC', 'ND', 'OH', 'OK', 'OR', 'PA', 'RI', 'SC',
    'SD', 'TN', 'TX', 'UT', 'VT', 'VA', 'WA', 'WV', 'WI', 'WY', 'DC',
})

US_STATE_NAMES: frozenset[str] = frozenset({
    'alabama', 'alaska', 'arizona', 'arkansas', 'california', 'colorado',
    'connecticut', 'delaware', 'florida', 'georgia', 'hawaii', 'idaho',
    'illinois', 'indiana', 'iowa', 'kansas', 'kentucky', 'louisiana',
    'maine', 'maryland', 'massachusetts', 'michigan', 'minnesota',
    'mississippi', 'missouri', 'montana', 'nebraska', 'nevada',
    'new hampshire', 'new jersey', 'new mexico', 'new york',
    'north carolina', 'north dakota', 'ohio', 'oklahoma', 'oregon',
    'pennsylvania', 'rhode island', 'south carolina', 'south dakota',
    'tennessee', 'texas', 'utah', 'vermont', 'virginia', 'washington',
    'west virginia', 'wisconsin', 'wyoming', 'district of columbia',
})


class VariableClassifier:
    """
    Auto-detects whether each column is Nominal, Ordinal, Interval/Ratio, Date,
    or Location.

    Heuristic priority:
      1. Object/string column where ≥80% of values parse as dates → Date
      2. Object/string column where ≥70% of values are US state abbreviations
         or full state names → Location
      3. Boolean → Nominal
      4. Non-numeric (object/category) →
           a. Try coerce to numeric; if ≥80% succeed → Interval/Ordinal by cardinality
           b. Otherwise → Nominal
      5. Numeric with high cardinality (>50% unique or >20 distinct) → Interval
      6. Numeric matching a Likert-style integer scale (e.g. 1–5, 0–7) → Ordinal
      7. Numeric with ≤15 unique values → Ordinal (conservative default)
      8. Everything else → Interval
    """

    ORDINAL_MAX_UNIQUE         = 15
    INTERVAL_CARDINALITY_RATIO = 0.5
    DATE_PARSE_MIN_FRAC        = 0.80   # fraction of non-null values that must parse as dates
    NUMERIC_COERCE_MIN_FRAC    = 0.80   # fraction that must coerce for numeric treatment
    LOCATION_MIN_FRAC          = 0.70   # fraction of values that must match US state names/abbrevs

    # ── Static helpers ────────────────────────────────────────────────────────

    @staticmethod
    def coerce_interval_series(series: pd.Series) -> pd.Series:
        """
        Strip currency signs, comparison operators, commas, and whitespace,
        then coerce to float.  Non-parseable values become NaN.

        Handles common export formats such as "$1,234.56", ">50", "< 20", ">=100".
        Pass-through for already-numeric series.
        """
        if pd.api.types.is_numeric_dtype(series):
            return series
        cleaned = (
            series.astype(str)
            .str.strip()
            .str.replace(r'[$,]', '', regex=True)
            .str.replace(r'^[><]=?', '', regex=True)
            .str.replace(r'\s+', '', regex=True)
        )
        return pd.to_numeric(cleaned, errors='coerce')

    @staticmethod
    def coerce_date_series(series: pd.Series) -> pd.Series:
        """
        Attempt to parse a series as datetime values.
        Non-parseable values become NaT.
        """
        return pd.to_datetime(series, infer_datetime_format=True, errors='coerce')

    # ── Core classification ───────────────────────────────────────────────────

    def classify(self, series: pd.Series) -> VariableType:
        clean = series.dropna()
        if clean.empty:
            return VariableType.NOMINAL

        # 1. Date check (object/string columns only — numeric columns are not dates)
        if series.dtype == object or str(series.dtype) == 'category':
            parsed_dates = VariableClassifier.coerce_date_series(clean)
            date_frac = parsed_dates.notna().mean()
            if date_frac >= self.DATE_PARSE_MIN_FRAC:
                return VariableType.DATE

        # 2. Location check — US state abbreviations or full state names
        if series.dtype == object or str(series.dtype) == 'category':
            upper_vals = clean.astype(str).str.strip().str.upper()
            abbrev_frac = upper_vals.isin(US_STATE_ABBREVS).mean()
            if abbrev_frac >= self.LOCATION_MIN_FRAC:
                return VariableType.LOCATION

            lower_vals = clean.astype(str).str.strip().str.lower()
            name_frac = lower_vals.isin(US_STATE_NAMES).mean()
            if name_frac >= self.LOCATION_MIN_FRAC:
                return VariableType.LOCATION

        # 3. Boolean
        if series.dtype == bool or str(series.dtype) == 'boolean':
            return VariableType.NOMINAL

        # 4. Non-numeric (object/category)
        if series.dtype == object or str(series.dtype) == 'category':
            coerced = VariableClassifier.coerce_interval_series(clean)
            valid_frac = coerced.notna().mean()
            if valid_frac >= self.NUMERIC_COERCE_MIN_FRAC:
                n_unique = coerced.nunique()
                n = len(coerced)
                if n_unique / n > self.INTERVAL_CARDINALITY_RATIO or n_unique > 20:
                    return VariableType.INTERVAL
                if self._is_likert_scale(coerced):
                    return VariableType.ORDINAL
                if n_unique <= self.ORDINAL_MAX_UNIQUE:
                    return VariableType.ORDINAL
                return VariableType.INTERVAL
            return VariableType.NOMINAL

        # 5. Datetime dtype
        if pd.api.types.is_datetime64_any_dtype(series):
            return VariableType.DATE

        # 6. Numeric
        if pd.api.types.is_numeric_dtype(series):
            n_unique = clean.nunique()
            n = len(clean)
            if n_unique / n > self.INTERVAL_CARDINALITY_RATIO or n_unique > 20:
                return VariableType.INTERVAL
            if self._is_likert_scale(clean):
                return VariableType.ORDINAL
            if n_unique <= self.ORDINAL_MAX_UNIQUE:
                return VariableType.ORDINAL
            return VariableType.INTERVAL

        return VariableType.NOMINAL

    def _is_likert_scale(self, series: pd.Series) -> bool:
        """True if the series looks like a contiguous integer rating scale (e.g. 1–5, 0–10)."""
        vals = series.dropna().unique()
        try:
            float_vals = [float(v) for v in vals]
        except (TypeError, ValueError):
            return False

        if not all(v == int(v) for v in float_vals):
            return False

        int_vals = sorted(int(v) for v in float_vals)
        n = len(int_vals)
        if n < 3 or n > 12:
            return False

        is_consecutive     = int_vals == list(range(int_vals[0], int_vals[-1] + 1))
        starts_at_zero_or_one = int_vals[0] in (0, 1)
        ends_reasonably    = int_vals[-1] in range(4, 13)

        return is_consecutive and starts_at_zero_or_one and ends_reasonably

    def classify_all(self, df: pd.DataFrame) -> dict[str, VariableType]:
        return {col: self.classify(df[col]) for col in df.columns}
