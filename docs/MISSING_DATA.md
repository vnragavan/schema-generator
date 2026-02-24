# Missing Data

The schema generation explicitly ignores missing or structurally null values during extraction. 

## Dropped Values (Silent)
The current implementation mathematically omits NaNs under `numpy.isfinite()` when computing minimums and maximums for bounding constraints, and specifically calls `pandas.dropna()` when capturing unique domain strings.

Because missingness rates are not tracked intrinsically during extraction, **the schema cannot be explicitly used to validate whether a synthetic dataset faithfully reproduced statistical missingness patterns or missing variables** from the base dataset. 

If this behaves paradoxically in your modeling workflow, you must pre-compute missingness rates mathematically *externally* via Pandas/R, and explicitly append them as JSON properties to the output payload via a custom `--constraints-file`.
