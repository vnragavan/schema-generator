# `target_spec` File Reference

Use `--target-spec-file <path.json>` when you want explicit target metadata.

## Purpose

- Define single-target, multi-target, or survival target roles explicitly.
- Avoid ambiguity from command-line inference.
- Share a stable target contract across teams.

## Accepted structure

Top-level JSON object:

```json
{
  "targets": ["target_a", "target_b"],
  "kind": "multi_target",
  "primary_target": "target_a",
  "dtypes": {
    "target_a": "numeric",
    "target_b": "categorical"
  }
}
```

## Fields

- `targets` (required)
  - List of target column names.
- `kind` (optional but recommended)
  - Typical values:
    - `single`
    - `multi_target`
    - `survival_pair`
- `primary_target` (optional)
  - Default target for consumers that need one canonical output.
  - Not mandatory when multiple targets exist.
- `dtypes` (optional)
  - Mapping of each target to logical dtype (`numeric` / `categorical` / other labels used by your workflow).

## Survival-pair convention

For survival use case:

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

The schema generator will also add survival-oriented cross-column constraints in `constraints`.

## If you do not provide this file

Toolkit can still infer target metadata from CLI:

- `--target-col`
- `--target-cols`
- `--target-kind`
- `--survival-event-col`
- `--survival-time-col`

`--target-spec-file` takes precedence when provided.
