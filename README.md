# Schema Toolkit (Standalone)

Self-contained toolkit to generate typed schema contracts from tabular data.

## What this project provides

- `schema_toolkit/prepare_schema.py`
  - Generates a schema JSON from CSV/TSV-like input.
  - Supports:
    - delimiter inference
    - typed columns (`continuous`, `integer`, `categorical`, `ordinal`)
    - binary inference for numeric 2-valued fields (e.g., `0/1`, `1/2`)
    - GUID/UUID identifier detection
    - datetime inference (mixed formats) with `datetime_spec`
    - optional multi-target / survival target definitions
    - optional user-supplied extra files (`column_types`, `target_spec`, `constraints`)

- `schema_toolkit/render_datetime.py`
  - Converts epoch-ns datetime columns back to string format using `datetime_spec`.

- `examples/*.sample.json`
  - Templates for additional files users can provide.

## Installation

Use Python 3.9+.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

## Quick start

```bash
python schema_toolkit/prepare_schema.py \
  --data data/my_dataset.csv \
  --out out/my_schema.json \
  --dataset-name my_dataset \
  --target-col target \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes
```

## Extra definition files (recommended)

You can refine schema behavior by providing additional files.

### 1) Column type overrides (`--column-types`)

Use this when you know certain fields are ordinal/categorical/numeric regardless of automatic inference.

Example:

```json
{
  "education-num": {"type": "ordinal", "domain": [1, 2, 3, 4, 5]},
  "risk_level": {"type": "ordinal", "domain": ["low", "medium", "high"]},
  "patient_id": {"type": "categorical"}
}
```

Detailed reference: `docs/COLUMN_TYPES.md`

### 2) Target spec file (`--target-spec-file`)

Use this to define multi-target or survival semantics in one file.

Example:

```json
{
  "targets": ["event", "time_to_event"],
  "kind": "survival_pair",
  "primary_target": "event",
  "dtypes": {
    "event": "numeric",
    "time_to_event": "numeric"
  }
}
```

Detailed reference: `docs/TARGET_SPEC.md`

### 3) Additional constraints (`--constraints-file`)

Generated constraints are always produced automatically.  
This file lets you add/override project-specific rules.

Example:

```json
{
  "column_constraints": {
    "time_to_event": {"min_exclusive": 0},
    "patient_id": {"semantic_role": "identifier"}
  },
  "cross_column_constraints": [
    {
      "name": "event_time_relation",
      "type": "survival_pair",
      "event_col": "event",
      "time_col": "time_to_event",
      "event_allowed_values": [0, 1],
      "time_min_exclusive": 0
    }
  ],
  "row_group_constraints": [
    {
      "name": "one_record_per_patient",
      "group_by": ["patient_id"],
      "rule": "max_rows_per_group",
      "value": 1
    }
  ]
}
```

Detailed reference: `docs/CONSTRAINTS.md`

## Full command (with additional files)

```bash
python schema_toolkit/prepare_schema.py \
  --data data/my_dataset.csv \
  --out out/my_schema.json \
  --dataset-name my_dataset \
  --target-col event \
  --column-types examples/column_types.sample.json \
  --target-spec-file examples/target_spec.sample.json \
  --constraints-file examples/constraints.sample.json \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes \
  --delimiter auto
```

## Datetime behavior

- Internally stored as numeric epoch-ns (`integer`) for model compatibility.
- Original rendering intent recorded in `datetime_spec`.
- Use `render_datetime.py` to convert synthesized numeric datetime columns back to formatted strings.

Example:

```bash
python schema_toolkit/render_datetime.py \
  --data out/synthetic.csv \
  --schema out/my_schema.json \
  --out out/synthetic_rendered.csv
```

## Output contract (top-level keys)

- `schema_version`
- `dataset`
- `target_col`
- `label_domain`
- `public_bounds`
- `public_categories`
- `column_types`
- `datetime_spec`
- `target_spec` (optional)
- `constraints`
  - `column_constraints`
  - `cross_column_constraints`
  - `row_group_constraints`
- `provenance`

## Notes

- If source data is private, inferred metadata should not automatically be treated as public.
- Review schema output before using it in strict privacy workflows.
