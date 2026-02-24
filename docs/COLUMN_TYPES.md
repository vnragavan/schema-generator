# `column_types` File Reference

Use `--column-types <path.json>` to override automatic type inference.

## Purpose

- Force semantically correct types (for example, mark a score as `ordinal`).
- Provide explicit allowed domains for categorical/ordinal fields.
- Prevent ambiguous auto-detection for edge-case columns.

## Accepted structure

Top-level JSON object:

```json
{
  "column_name_a": "ordinal",
  "column_name_b": {
    "type": "categorical",
    "domain": ["A", "B", "C"]
  }
}
```

Each column entry supports:

- `string` shorthand: one of
  - `continuous`
  - `integer`
  - `categorical`
  - `ordinal`
- `object` form:
  - `type` (required): one of the same 4 values
  - `domain` (optional): list of values, meaningful for `categorical`/`ordinal`

## Semantics by type

- `continuous`
  - Real-valued field.
  - Generator uses bounds (`public_bounds`).
- `integer`
  - Integer-valued field.
  - Generator uses bounds (`public_bounds`).
- `categorical`
  - Unordered labels.
  - If `domain` provided, it is copied to `public_categories`.
- `ordinal`
  - Ordered labels.
  - If `domain` provided, order is preserved.

## Recommended usage

- Always provide `domain` for important `ordinal` fields.
- Use overrides for business-critical columns where type ambiguity is risky.
- Keep values in `domain` JSON-serializable; strings are safest.

## Example

```json
{
  "education_num": {
    "type": "ordinal",
    "domain": [1, 2, 3, 4, 5, 6]
  },
  "risk_band": {
    "type": "ordinal",
    "domain": ["low", "medium", "high"]
  },
  "patient_id": "categorical"
}
```
