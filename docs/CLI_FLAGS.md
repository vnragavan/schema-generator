# CLI Flags Reference

This document is the complete CLI reference for:

- `schema_toolkit/prepare_schema.py`
- `schema_toolkit/render_datetime.py`

---

## 1) `prepare_schema.py`

### Required arguments

- `--data <path>`
  - **Type:** path
  - **Required:** yes
  - Input tabular file (CSV/TSV-like).

- `--out <path>`
  - **Type:** path
  - **Required:** yes
  - Output schema JSON path.

### Dataset and target metadata

- `--dataset-name <string>`
  - **Default:** inferred from input filename stem
  - Explicit dataset identifier to write into schema.

- `--target-col <string>`
  - **Default:** auto-inferred from common names (`target`, `income`, `label`, `class`, `outcome`) when present
  - Primary target column name.

- `--target-cols <csv-list>`
  - **Default:** none
  - Comma-separated list of target columns for multi-target schemas (alternative to `--target-spec-file`).
  - Example: `event,time_to_event`

- `--target-kind <string>`
  - **Default:** inferred (`single` or `multi_target`)
  - Manually specify the target semantic kind (`single`, `multi_target`, `survival_pair`, etc.).

- `--survival-event-col <string>`
  - **Default:** none
  - Shorthand to set the event indicator column of a survival pair directly on the CLI.

- `--survival-time-col <string>`
  - **Default:** none
  - Shorthand to set the time-to-event column of a survival pair directly on the CLI.

### User-provided definition files

- `--column-types <path.json>`
  - **Default:** none
  - Column type/domain overrides.
  - See: `docs/COLUMN_TYPES.md`

- `--target-spec-file <path.json>`
  - **Default:** none
  - Explicit target metadata file.
  - See: `docs/TARGET_SPEC.md`

- `--constraints-file <path.json>`
  - **Default:** none
  - Additional constraints merged with auto-generated constraints.
  - See: `docs/CONSTRAINTS.md`

### Parsing and inference controls

- `--delimiter <string>`
  - **Default:** `auto`
  - Input field separator. Uses heuristics when set to `auto`. 

- `--pad-frac <float>`
  - **Default:** `0.0`
  - Global fallback padding fraction for integer/continuous bounds in `public_bounds`.

- `--pad-frac-integer <float>`
  - **Default:** unset (falls back to `--pad-frac`)
  - Per-type padding for integer columns only.

- `--pad-frac-continuous <float>`
  - **Default:** unset (falls back to `--pad-frac`)
  - Per-type padding for continuous columns only.

- `--infer-categories`
  - **Default:** off
  - Infer category domains for non–integer/continuous columns.

- `--max-categories <int>`
  - **Default:** `200`
  - Maximum number of unique values to enumerate into `public_categories`. If unique count exceeds this threshold, domain is not emitted.

- `--infer-binary-domain`
  - **Default:** off
  - For integer 2-valued fields (e.g., `0/1`, `1/2`), infer ordinal domain in `public_categories` and **promotes the column type from "integer" to "ordinal"**.
  - **Warning**: Downstream consumers expecting structural integers for 0/1 booleans will receive an ordinal type instead. 

- `--infer-datetimes`
  - **Default:** off
  - Enable datetime-like parsing for temporal columns (including mixed string formats).

- `--datetime-min-parse-frac <float>`
  - **Default:** `0.95`
  - Minimum fraction of non-null parses required before a column is treated structurally as a datetime instead of a string categorical. 

- `--datetime-output-format <string>`
  - **Default:** `preserve`
  - Override the output format string applied to all extracted datetime columns. `preserve` defaults to inferring the best-effort pattern directly from the series values per-column. 

- `--guid-min-match-frac <float>`
  - **Default:** `0.95`
  - Minimum fraction of values matching the UUID regex before a column is formally classified as a GUID identity.

- `--redact-source-path`
  - **Default:** `False`
  - Writes a placeholder string instead of the real executing local directory path within the JSON payload `provenance.source_csv`. Prominently recommended for sharing federated objects. 

- `--target-is-classifier`
  - **Default:** `False`
  - Forces the generator to populate `label_domain` and `public_categories` for the target variable, even if it is mathematically inferred as an integer column. This is a critical escape-hatch for downstream utility evaluation frameworks (like SDMetrics) that require explicit bounding domain lists to configure classification metrics properly.

- `--no-publish-label-domain`
  - **Default:** `False`
  - Manual flag to override and suppress target variables from leaking explicit enumeration domains into `label_domain` and `public_categories`. Useful for reducing sensitive or low-volume prediction label leaks.

---

## 2) `render_datetime.py`

### Required arguments

- `--data <path>`
  - **Type:** path
  - **Required:** yes
  - Input CSV expected to contain epoch-ns datetime columns.

- `--schema <path>`
  - **Type:** path
  - **Required:** yes
  - Schema JSON with `datetime_spec`.

- `--out <path>`
  - **Type:** path
  - **Required:** yes
  - Output CSV path after datetime rendering.

### Optional arguments

- `--keep-original`
  - **Default:** `False`
  - Keeps the original epoch-ns column structurally and simultaneously writes the newly rendered string datetime payload uniquely to a new `<col>__rendered` column rather than replacing the source column in-place. 

---

## 3) Precedence and interactions

- If `--target-spec-file` is provided, it takes precedence over CLI target composition flags (`--target-cols`, survival flags).
- `--column-types` overrides automatic column typing.
- Padding precedence is: `--pad-frac-integer` / `--pad-frac-continuous` then `--pad-frac`.
- `categorical`/`ordinal` columns do not use bounds padding.
- Datetime parsing only runs when `--infer-datetimes` is enabled.
