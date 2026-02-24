# Standard Medical Constraints Vocabulary

To guarantee that synthetic data algorithms generate biologically and temporally possible patients, `schema-generator` supports a standard vocabulary of constraint classes. Because the generator functions as a "metadata contract engine," these constraints are passed via the `--constraints-file` argument and embedded into the final `schema.json`.

Downstream synthetic data generators (such as SDV, Gretel, or custom Diffusion/GAN frameworks) and validators (like Great Expectations) can parse this standard vocabulary to construct rejection samplers, loss function penalties, or programmatic filters.

The standard defines **six fundamental vocabularies** capable of capturing the physical laws of a flat tabular medical dataset.

---

## 1. Inequality (Chronological & Physical Bounds)
**Purpose:** Enforces an absolute boundary where one column must mathematically be less than or equal to another. Highly critical for the "Arrow of Time" in healthcare or upper limit physics.
**Location:** `cross_column_constraints`

### Medical Example:
A patient cannot be discharged before they are admitted.
```json
{
  "constraint_class": "Inequality",
  "name": "hospital_stay_chronology",
  "low_column": "admission_datetime",
  "high_column": "discharge_datetime",
  "strict_boundaries": false
}
```

---

## 2. FixedCombinations (Logical Gates & Implication)
**Purpose:** Defines the whitelist of permissible intersections between categorical variables. This prevents mutually exclusive biological traits or contradictory diagnoses from appearing in the same synthetic patient.
**Location:** `cross_column_constraints`

### Medical Example:
Pregnancy logic implies strict correlation with biological sex. Males cannot have a pregnant status.
```json
{
  "constraint_class": "FixedCombinations",
  "name": "pregnancy_sex_logic",
  "columns": ["pregnancy_status", "biological_sex"],
  "valid_combinations": [
    [0, "M"],
    [0, "F"],
    [1, "F"]
  ]
}
```

---

## 3. CompositionalSum (Formulaic Equality)
**Purpose:** Guarantees that a parent variable equals the strict mathematical sum of its constituent child variables. Extremely important for clinical scoring systems and health economic cost accounting.
**Location:** `cross_column_constraints`

### Medical Example:
A patient's total hospital cost must exactly match the sum of itemized billing components.
```json
{
  "constraint_class": "CompositionalSum",
  "name": "total_cost_accounting",
  "total_column": "total_hospital_cost",
  "component_columns": ["procedure_cost", "medication_cost", "room_board_cost"],
  "tolerance": 0.01 
}
```

---

## 4. PiecewiseBounds (Dynamic Reference Ranges)
**Purpose:** Shifts mathematical minimum/maximum boundaries dynamically based on the state of a continuous conditioning variable (like Age or Weight).
**Location:** `cross_column_constraints`

### Medical Example:
Resting heart rates have fundamentally different acceptable bounds depending on the age of the patient.
```json
{
  "constraint_class": "PiecewiseBounds",
  "name": "age_adjusted_heart_rate",
  "target_column": "heart_rate_bpm",
  "condition_column": "age_years",
  "conditions": [
    {
      "criteria": "< 1", 
      "bounds": {"min": 100, "max": 180}
    },
    {
      "criteria": ">= 18", 
      "bounds": {"min": 40, "max": 110}
    }
  ]
}
```

---

## 5. MonotonicOrdering (Longitudinal Progression)
**Purpose:** Validates row-by-row temporal progression for longitudinal panel data, ensuring chronological sorting or unidirectional disease progression for a grouped entity.
**Location:** `row_group_constraints`

### Medical Example:
A patient's visits over time must run sequentially forward.
```json
{
  "constraint_class": "MonotonicOrdering",
  "name": "sequential_patient_visits",
  "entity_column": "patient_id",
  "sort_column": "visit_timestamp",
  "trend": "strictly_increasing"
}
```

---

## 6. RegexMatch (Strict Lexical Formatting)
**Purpose:** Preserves syntactic validation rather than mathematical validation, ensuring output strings map accurately to complex international coding definitions.
**Location:** `column_constraints`

### Medical Example:
ICD-10 clinical diagnostic codes must strictly follow their predefined alphanumeric pattern (Letter, Two Digits, Dot, Trailing Digits) to be useful for downstream systems.
```json
{
  "icd_10_code": {
    "constraint_class": "RegexMatch",
    "pattern": "^[A-Z][0-9]{2}(\\.[0-9]{1,4})?$"
  }
}
```
