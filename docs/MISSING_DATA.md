# Missing Data

The schema generation explicitly ignores missing or structurally null values during extraction. 

## Dropped Values (Silent)
The current implementation mathematically omits NaNs under `numpy.isfinite()` when computing minimums and maximums for bounding constraints, and specifically calls `pandas.dropna()` when capturing unique domain strings.

Because the minimum and maximum boundaries explicitly drop null representations mathematically to calculate clean integer/continuous limits (`numpy.isfinite()`), the schema generator implements dedicated tracking to prevent data leakage around missingness percentages.

## `missing_value_rates` Property
The `schema.json` universally tracks the proportion of missing values natively for every feature during extraction. This allows synthetic validators to independently cross-reference whether an AI model perfectly recreated the underlying sparsity matrix.

```json
  "missing_value_rates": {
    "patient_id": 0.0,
    "age_years": 0.25,
    "discharge_datetime": 0.25
  }
```
