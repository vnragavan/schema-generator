# `constraints` File Reference

Use `--constraints-file <path.json>` to extend or override generated constraints.

## Purpose

- Capture semantic rules beyond basic type/domain information.
- Define column-level, cross-column, and row-group rules.
- Encode survival semantics and relational assumptions explicitly.

## Accepted structure

Top-level JSON object with optional keys:

- `column_constraints` (object)
- `cross_column_constraints` (array)
- `row_group_constraints` (array)

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

## Merge behavior

Constraints are generated automatically first, then merged with your file:

- `column_constraints`: shallow update by column key (your keys override/add fields).
- `cross_column_constraints`: appended.
- `row_group_constraints`: appended.

## Common patterns

### Column-level

- range rules:
  - `min`, `max`, `min_exclusive`, `max_exclusive`
- semantic role:
  - `semantic_role: "identifier"`
- controlled values:
  - `allowed_values: [...]`

### Cross-column

- survival pair relation (`event` + `time`)
- conditional dependencies (`if A then B`)
- pair consistency checks

### Row-group

- uniqueness constraints per key
- max rows per entity
- monotonic or temporal ordering rules (documented as metadata for downstream validators)

## Notes

- These constraints are metadata contract entries; enforcement is handled by downstream consumers/validators.
- Keep constraints deterministic and machine-readable where possible.
