# End-to-End Use Cases

This page provides runnable examples for:

- Adult dataset
- Breast Cancer dataset
- NCCTG Lung Cancer dataset (survival example)

Each example includes command(s) and expected outputs.

---

## 0) Setup

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

Create an output folder:

```bash
mkdir -p outputs/schemas
```

---

## 1) Adult dataset example

### Input assumptions

- CSV path: `data/adult.csv`
- Label column: `income`
- You may want to mark `education-num` as ordinal via a `column_types` file.

### Command

```bash
python schema_toolkit/prepare_schema.py \
  --data data/adult.csv \
  --out outputs/schemas/adult_schema.json \
  --dataset-name adult \
  --target-col income \
  --column-types inputs/schemas/column_types.sample.json \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes
```

### Expected output file

- `outputs/schemas/adult_schema.json`

### Expected output content (high level)

- `schema_version`
- `dataset: "adult"`
- `target_col: "income"`
- `label_domain` (typically `<=50K`, `>50K`)
- `column_types` with categorical/integer/continuous/ordinal assignments
- `public_categories` for categorical columns (including binary categories like `sex`, `income`)
- `public_bounds` for integer/continuous columns
- `constraints` block (`column_constraints`, etc.)
- `provenance` with delimiter and inference settings

---

## 2) Breast Cancer dataset example

### Input assumptions

- CSV path: `data/breast_cancer.csv`
- Label column: `target`

### Command

```bash
python schema_toolkit/prepare_schema.py \
  --data data/breast_cancer.csv \
  --out outputs/schemas/breast_cancer_schema.json \
  --dataset-name breast_cancer \
  --target-col target \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes
```

### Expected output file

- `outputs/schemas/breast_cancer_schema.json`

### Expected output content (high level)

- `schema_version`
- `dataset: "breast_cancer"`
- `target_col: "target"`
- `label_domain` usually `["0","1"]`
- mostly integer/continuous `column_types` + categorical target
- `public_bounds` for most feature columns
- `constraints` and `provenance`

---

## 3) NCCTG Lung Cancer survival example

Use this example for survival-focused schema definitions.

### Input assumptions

- CSV path: `data/ncctg_lung.csv`
- Event column: `event`
- Time column: `time_to_event`
- Survival relation encoded in `target_spec` and constraints.

### Option A: Use sample target/constraints files

```bash
python schema_toolkit/prepare_schema.py \
  --data data/ncctg_lung.csv \
  --out outputs/schemas/ncctg_lung_schema.json \
  --dataset-name ncctg_lung \
  --target-col event \
  --target-spec-file inputs/schemas/target_spec.sample.json \
  --constraints-file inputs/schemas/constraints.sample.json \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes
```

### Option B: Use CLI survival flags only

```bash
python schema_toolkit/prepare_schema.py \
  --data data/ncctg_lung.csv \
  --out outputs/schemas/ncctg_lung_schema.json \
  --dataset-name ncctg_lung \
  --target-col event \
  --target-cols event,time_to_event \
  --target-kind survival_pair \
  --survival-event-col event \
  --survival-time-col time_to_event \
  --infer-categories \
  --infer-binary-domain \
  --infer-datetimes
```

### Expected output file

- `outputs/schemas/ncctg_lung_schema.json`

### Expected output content (high level)

- `target_spec.kind: "survival_pair"`
- `target_spec.targets: ["event","time_to_event"]`
- survival constraint in `constraints.cross_column_constraints`, including:
  - `type: "survival_pair"`
  - `event_col`, `time_col`
  - event domain and minimum-time rule
- binary/ordinal treatment for appropriate columns (for example `status`, `sex` if two-valued integer)

---

## 4) Advanced Medical/Survival Routing (Dummy Dataset)

Use this example to see how the toolkit resolves common data structure concerns:
1. Converting `0-1` numeric columns to boolean domains (`--infer-binary-domain`).
2. Retaining `Yes/No` textual structures dynamically (`--infer-categories`).
3. Configuring survival constraints and dropping baseline classification metrics via multi-column inputs.

### Input assumptions
- CSV path: `data/dummy_survival_concerns.csv`
- Event column (integer boolean): `event_occurred`
- Time column (continuous): `survival_duration`

### Command
```bash
python schema_toolkit/prepare_schema.py \
  --data data/dummy_survival_concerns.csv \
  --out outputs/schemas/out_survival_concerns_schema.json \
  --dataset-name survival_concerns \
  --target-cols event_occurred,survival_duration \
  --target-kind survival_pair \
  --survival-event-col event_occurred \
  --survival-time-col survival_duration \
  --infer-binary-domain \
  --infer-categories
```

### Expected output file
- `outputs/schemas/out_survival_concerns_schema.json`

### Expected output content (high level)
- Text-category variables (e.g. `Yes/No`) cleanly mapped to `categorical`.
- Boolean `0-1` numeric arrays forcefully mapped to `ordinal` avoiding continuous padding.
- `label_domain: []` explicitly emptying to gracefully bypass downstream classifiers.
- Multi-column `survival_pair` dynamically constraining sequential bounds.

---

## 5) Datetime rendering (post-processing synthetic CSVs)

If a generated/synthetic CSV contains epoch-ns datetime columns and your schema has `datetime_spec`, convert them back to native string format:

```bash
python schema_toolkit/render_datetime.py \
  --data outputs/schemas/synthetic.csv \
  --schema outputs/schemas/ncctg_lung_schema.json \
  --out outputs/schemas/synthetic_rendered.csv
```

### Expected output file

- `outputs/schemas/synthetic_rendered.csv`

Datetime columns referenced by `datetime_spec` are rendered as formatted strings.

---

## 6) Summary of produced artifacts

From `prepare_schema.py`:

- One schema JSON at `--out` with:
  - types (`column_types`)
  - domains (`public_categories`)
  - integer/continuous ranges (`public_bounds`)
  - optional `datetime_spec`
  - optional `target_spec`
  - `constraints`
  - `provenance`

From `render_datetime.py`:

- One rendered CSV at `--out` with datetime strings (replacing source columns unless `--keep-original` is used).

---

## 7) Dataset references

- Adult Census Income (UCI):
  - https://archive.ics.uci.edu/dataset/2/adult
- Breast Cancer Wisconsin (Diagnostic):
  - https://scikit-learn.org/stable/datasets/toy_dataset.html#breast-cancer-dataset
- NCCTG Lung Cancer (survival dataset in `lifelines`):
  - https://lifelines.readthedocs.io/en/latest/lifelines.datasets.html
- Dummy Survival Concerns:
  - Synthetic dataset specifically built for demonstrating multi-target and classification inference edge-cases.
