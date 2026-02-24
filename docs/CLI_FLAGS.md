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
  - Comma-separated list for multi-target setup.
  - Example: `event,time_to_event`

- `--target-kind <string>`
  - **Default:** inferred (`single` or `multi_target`)
  - Target semantic kind (`single`, `multi_target`, `survival_pair`, etc.).

- `--survival-event-col <string>`
  - **Default:** none
  - Event indicator column for survival mode.

- `--survival-time-col <string>`
  - **Default:** none
  - Time-to-event column for survival mode.

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
  - Input field separator.
  - `auto` infers delimiter (supports common delimiters like comma, semicolon, tab, pipe).
  - You can set explicit delimiter such as `,`, `;`, `\t`, `|`.

- `--pad-frac <float>`
  - **Default:** `0.0`
  - Global fallback padding fraction for integer/continuous bounds in `public_bounds`.

- `--pad-frac-integer <float>`
  - **Default:** unset (falls back to `--pad-frac`)
  - Padding fraction for columns typed as `integer`.
  - Integer bounds are rounded outward to preserve integer semantics.

- `--pad-frac-continuous <float>`
  - **Default:** unset (falls back to `--pad-frac`)
  - Padding fraction for columns typed as `continuous`.

- `--infer-categories`
  - **Default:** off
  - Infer category domains for non–integer/continuous columns.

- `--max-categories <int>`
  - **Default:** `200`
  - Maximum unique categories allowed for inferred categorical domain export.
  - If unique count exceeds this threshold, domain is not emitted.

- `--infer-binary-domain`
  - **Default:** off
  - For integer 2-valued fields (e.g., `0/1`, `1/2`), infer ordinal domain in `public_categories`.

- `--infer-datetimes`
  - **Default:** off
  - Enable datetime-like parsing for temporal columns (including mixed string formats).

- `--datetime-min-parse-frac <float>`
  - **Default:** `0.95`
  - Minimum parse success fraction required to treat a string column as datetime-like.

- `--datetime-output-format <string>`
  - **Default:** `preserve`
  - Datetime rendering format metadata for `datetime_spec`.
  - `preserve`: best-effort format inferred from source values.
  - Or pass explicit `strftime` format, e.g. `%Y-%m-%dT%H:%M:%S`.

- `--guid-min-match-frac <float>`
  - **Default:** `0.95`
  - Fraction threshold for classifying a string column as GUID/UUID-like identifier.

- `--redact-source-path`
  - **Default:** off
  - If set, `provenance.source_csv` is written as `example_data_path_to_csv_file` instead of an absolute/local file path.

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
  - **Default:** off
  - If set, original epoch-ns datetime columns are retained and rendered values are written to `<column>__rendered`.
  - If not set, source datetime columns are replaced with rendered strings.

---

## 3) Precedence and interactions

- If `--target-spec-file` is provided, it takes precedence over CLI target composition flags (`--target-cols`, survival flags).
- `--column-types` overrides automatic column typing.
- `--constraints-file` is merged on top of generated constraints:
  - `column_constraints`: updated by key
  - `cross_column_constraints`: appended
  - `row_group_constraints`: appended
- Padding precedence is:
  - `--pad-frac-integer` for `integer` columns when provided
  - `--pad-frac-continuous` for `continuous` columns when provided
  - otherwise global `--pad-frac`
- `categorical`/`ordinal` columns do not use bounds padding.
- Datetime parsing only runs when `--infer-datetimes` is enabled.

---

## 4) Example (full option usage)

```bash
python schema_toolkit/prepare_schema.py \
  --data data/ncctg_lung.csv \
  --out out/ncctg_lung_schema.json \
  --dataset-name ncctg_lung \
  --target-col event \
  --column-types examples/column_types.sample.json \
  --target-spec-file examples/target_spec.sample.json \
  --constraints-file examples/constraints.sample.json \
  --delimiter auto \
  --pad-frac 0.0 \
  --pad-frac-integer 0.0 \
  --pad-frac-continuous 0.02 \
  --infer-categories \
  --max-categories 200 \
  --infer-binary-domain \
  --infer-datetimes \
  --datetime-min-parse-frac 0.95 \
  --datetime-output-format preserve \
  --guid-min-match-frac 0.95
```
