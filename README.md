# Schema Toolkit (Standalone)

Self-contained toolkit to generate typed schema contracts from tabular data.

## What this project provides

> **Privacy Note:** Be heavily aware that `public_bounds` statically records the exact mathematical minimum and maximum boundaries of each processed numeric column by default. Additionally, `public_categories` functionally enumerates *all* uniquely occurring strings inside categorical variables natively verbatim. Finally, `provenance.source_csv` stamps your exact operating OS file-structure into the json object automatically. **You should review these fields carefully before distributing a schema publicly.** Best practice dictations advise adopting `--pad-frac`, restricting domains firmly using `--max-categories`, and actively applying `--redact-source-path` to mitigate PII structural exposures.

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

*(Note: Within survival pairing array lists, `targets[0]` always defaults identically into the Event component, while `targets[1]` permanently attaches as the Time component).*

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

- Internally stored as integer epoch-ns for model compatibility.
- Original rendering intent recorded in `datetime_spec`.
- Use `render_datetime.py` to convert synthesized epoch-ns datetime columns back to formatted strings.

**Datetime Algorithm Specifications:** When the `--infer-datetimes` flag passes activation checks, the software cascades strings against 5 core parse strategies (UTC combinations of mixed, standard, dayfirst, yearfirst, and bidirectional). Passing minimum fractions matching the `--datetime-min-parse-frac` threshold enforces datetime typings. *Note:* Because random sampling is deactivated entirely, extremely large multi-million row matrices scanning iteratively against date permutations can incur large execution loops. 

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
- `public_bounds`: *For each numeric entity, a discrete 2-element index `[min, max]` mapping mathematical bounds extracted strictly across the feature distribution directly, natively unpadded structurally internally without active `--pad-frac`.*
- `public_categories`: *For categorical and ordinal targets, a recursively sorted explicit array listing comprehensively resolving non-NaN strings observed natively directly.* 
- `column_types`
- `datetime_spec`
- `target_spec` (optional)
- `constraints`
  - `column_constraints`
  - `cross_column_constraints`
  - `row_group_constraints`
- `provenance`: *Diagnostic footprint capturing timestamps (`generated_at_utc`), explicit boolean CLI execution parameters utilized globally natively strings, and raw source pathways mapping recursively to the `source_csv` structurally.*

## Notes

- **Warning:** Executing the internal `--infer-binary-domain` command does not functionally merely attach standard array domains locally onto existing binary sets. Activating this setting actively fundamentally strips mapping configurations promoting arrays natively outward toward `ordinal` structures functionally altering downstream schemas significantly permanently.
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
