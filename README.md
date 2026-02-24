# Schema Toolkit (Standalone)

Self-contained toolkit to generate typed schema contracts from tabular data.

## What this project provides

> **Privacy Note:** Be aware that `public_bounds` records the exact minimum and maximum of each processed numeric column by default. Additionally, `public_categories` lists all unique values for categorical variables. Finally, `provenance.source_csv` saves your local file path into the json object. **You should review these fields carefully before distributing a schema publicly.** Best practices advise using `--pad-frac`, restricting domains firmly with `--max-categories`, and using `--redact-source-path` to mitigate PII exposures.

- `schema_toolkit/prepare_schema.py`
  - Generates a schema JSON from CSV/TSV-like input.
  - Supports:
    - delimiter inference
    - typed columns (`continuous`, `integer`, `categorical`, `ordinal`)
    - binary inference for integer 2-valued fields (e.g., `0/1`, `1/2`)
    - GUID/UUID identifier detection
    - datetime inference (mixed formats) with `datetime_spec`
    - optional multi-target / survival target definitions
    - optional user-supplied extra files (`column_types`, `target_spec`, `constraints`)

- `schema_toolkit/render_datetime.py`
  - Converts epoch-ns datetime columns back to string format using `datetime_spec`.

- `inputs/schemas/*.sample.json`
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

**Target Inference Fallbacks:** If `--target-col` is not supplied inside the execution loop directly, the application runs a heuristic verifying if any column names structurally exactly identically matches the keywords: `target`, `income`, `label`, `class`, or `outcome` sequentially. If none execute a match, `target_col` resolves dynamically to `None`. To prevent unanticipated variables capturing the outcome (such as a string `income` band feature), we strongly recommend you always explicitly route the target param via `--target-col`.

## Extra definition files (recommended)

You can refine schema behavior by providing additional files.

### 1) Column type overrides (`--column-types`)

Use this when you know certain fields are ordinal/categorical or integer/continuous regardless of automatic inference.

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
    "event": "categorical",
    "time_to_event": "integer"
  }
}
```

Detailed reference: `docs/TARGET_SPEC.md`

*(Note: Within survival pairing targets, `targets[0]` acts as the Event component, and `targets[1]` acts as the Time component).*

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
  --column-types inputs/schemas/column_types.sample.json \
  --target-spec-file inputs/schemas/target_spec.sample.json \
  --constraints-file inputs/schemas/constraints.sample.json \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes \
  --delimiter auto
```

## Datetime behavior

- Internally stored as integer epoch-ns for model compatibility.
- Original rendering intent recorded in `datetime_spec`.
- Use `render_datetime.py` to convert synthesized epoch-ns datetime columns back to formatted strings.

**Datetime Algorithm Specifications:** When the `--infer-datetimes` flag is used, the software attempts to parse strings using 5 core formats. Setting `--datetime-min-parse-frac` threshold determines whether a column is considered a datetime. *Note:* Processing very large datasets across multiple date permutations can take a long time. 

Example:

```bash
python schema_toolkit/render_datetime.py \
  --data out/synthetic.csv \
  --schema out/my_schema.json \
  --keep-original \
  --out out/synthetic_rendered.csv
```

**`render_datetime.py` specifics:**
- Enacting the `--keep-original` parameter explicitly retains the starting epoch-ns variable natively, allocating synthesized formatting values adjacent under `<col>__rendered` columns safely.
- If simulated epoch-ns integers violate boundaries previously identified functionally (stretching externally outwards), string outputs stringify normally regardless natively rendering without runtime boundary blockages.
- Standard generated datetimes are explicitly coerced safely into globally compliant `UTC` epochs, neutralizing original regional strings automatically.
- A hard runtime `SystemExitException` strictly crashes if schemas lack `datetime_spec` object dictionaries structurally correctly resolving representations.

## Output contract (top-level keys)

- `schema_version`
- `dataset`
- `target_col`
- `label_domain`
- `missing_value_rates`: *A mapping of every feature to its respective percentage of NaN/null values found during the extraction phase.*
- `public_bounds`: *For each numeric column, a `[min, max]` array. These bounds are exact unless `--pad-frac` is used to add padding.*
- `public_categories`: *For categorical and ordinal targets, a sorted list of all unique non-null values.* 
- `column_types`
- `datetime_spec`
- `target_spec` (optional)
- `constraints`
  - `column_constraints`
  - `cross_column_constraints`
  - `row_group_constraints`
- `provenance`: *Diagnostic footprint capturing timestamps (`generated_at_utc`), execution parameters, and the original `source_csv` path.*

## Notes

- **Warning:** Using `--infer-binary-domain` forces integer columns with exactly two values into `ordinal` categorical structures.
- If source data is private, inferred metadata should not automatically be treated as public.
- Review schema output carefully before using it globally across privacy workflows structurally. Validations and missing components should be mapped formally using reference `docs/MISSING_DATA.md` and `docs/PUBLIC_METADATA.md`.

## Dataset examples

See `docs/USE_CASES.md` for step-by-step commands and expected outputs for:

- Adult
- Breast Cancer
- NCCTG Lung Cancer (survival)

Pre-generated example outputs are available under:

- `outputs/schemas/adult_schema.json`
- `outputs/schemas/breast_cancer_schema.json`
- `outputs/schemas/ncctg_lung_schema.json`

## CLI reference

For a full flag-by-flag reference of all command options, see:

- `docs/CLI_FLAGS.md`
