#!/usr/bin/env python3
from __future__ import annotations

import argparse
import csv
import json
import re
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd

SCHEMA_VERSION = "1.3.0"

_UUID_RE = re.compile(
    r"^(?:"
    r"[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
    r"|[0-9a-fA-F]{32}"
    r"|\{[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}\}"
    r"|urn:uuid:[0-9a-fA-F]{8}-[0-9a-fA-F]{4}-[1-5][0-9a-fA-F]{3}-[89abAB][0-9a-fA-F]{3}-[0-9a-fA-F]{12}"
    r")$"
)


def _infer_target_col(cols: list[str]) -> str | None:
    for c in ["target", "income", "label", "class", "outcome"]:
        if c in cols:
            return c
    return None


def _parse_csv_list(v: str | None) -> list[str]:
    if not v:
        return []
    return [x.strip() for x in v.split(",") if x.strip()]


def _infer_csv_delimiter(path: Path) -> str:
    try:
        sample = path.read_text(encoding="utf-8", errors="ignore")[:8192]
        if not sample.strip():
            return ","
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
        d = getattr(dialect, "delimiter", ",")
        return d if d else ","
    except Exception:
        return ","


def _infer_target_dtype(df: pd.DataFrame, col: str) -> str:
    """Return schema dtype: integer, continuous, categorical, or ordinal."""
    if col not in df.columns:
        return "unknown"
    s = df[col]
    if not (pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s)):
        return "categorical"
    x = pd.to_numeric(s, errors="coerce")
    xn = x[np.isfinite(x)].to_numpy(dtype=float)
    if xn.size == 0:
        return "continuous"
    if np.all(np.isclose(xn, np.round(xn), atol=1e-8)):
        return "integer"
    return "continuous"


def _target_dtype_from_column_type(column_type: str | None) -> str | None:
    """Return schema dtype as-is: integer, continuous, categorical, or ordinal."""
    if not isinstance(column_type, str):
        return None
    t = column_type.strip().lower()
    if t in {"integer", "continuous", "categorical", "ordinal"}:
        return t
    return None


def _guess_datetime_output_format(raw: pd.Series) -> str:
    samples = pd.Series(raw, copy=False).astype("string").dropna().astype(str).str.strip()
    if samples.empty:
        return "%Y-%m-%dT%H:%M:%S"
    patterns = [
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d",
        "%d/%m/%Y %H:%M",
        "%d/%m/%Y",
        "%m-%d-%Y %H:%M",
        "%m-%d-%Y",
        "%Y/%m/%dT%H:%M:%SZ",
        "%Y/%m/%d %H:%M:%S",
        "%Y/%m/%d",
        "%Y.%m.%d %H:%M:%S",
        "%Y.%m.%d",
    ]
    for fmt in patterns:
        try:
            dt = pd.to_datetime(samples, format=fmt, errors="coerce")
            if float(dt.notna().mean()) >= 0.8:
                return fmt
        except Exception:
            continue
    return "%Y-%m-%dT%H:%M:%S"


def _maybe_parse_datetime_like(
    s: pd.Series, *, min_parse_frac: float
) -> tuple[pd.Series, bool, str | None]:
    if pd.api.types.is_datetime64_any_dtype(s):
        dt = pd.to_datetime(pd.Series(s, copy=False), errors="coerce")
        v = dt.astype("int64").astype("float64")
        v[dt.isna()] = np.nan
        return v, True, "%Y-%m-%dT%H:%M:%S"
    if pd.api.types.is_timedelta64_dtype(s):
        td = pd.to_timedelta(pd.Series(s, copy=False), errors="coerce")
        v = td.astype("int64").astype("float64")
        v[td.isna()] = np.nan
        return v, True, "%Y-%m-%dT%H:%M:%S"

    if s.dtype == "object" or pd.api.types.is_string_dtype(s):
        raw = pd.Series(s, copy=False).astype("string")
        raw = raw.replace(
            {
                "": pd.NA,
                " ": pd.NA,
                "null": pd.NA,
                "NULL": pd.NA,
                "none": pd.NA,
                "None": pd.NA,
                "nan": pd.NA,
                "NaN": pd.NA,
                "nat": pd.NA,
                "NaT": pd.NA,
            }
        )
        parse_attempts = [
            {"format": "mixed", "utc": True},
            {"utc": True},
            {"dayfirst": True, "utc": True},
            {"yearfirst": True, "utc": True},
            {"dayfirst": True, "yearfirst": True, "utc": True},
        ]
        best_dt = None
        best_frac = -1.0
        for kw in parse_attempts:
            try:
                dt = pd.to_datetime(raw, errors="coerce", **kw)
                frac = float(dt.notna().mean())
                if frac > best_frac:
                    best_frac = frac
                    best_dt = dt
            except Exception:
                continue
        if best_dt is not None and best_frac >= float(min_parse_frac):
            v = best_dt.astype("int64").astype("float64")
            v[best_dt.isna()] = np.nan
            return v, True, _guess_datetime_output_format(raw)
    return s, False, None


def _is_guid_like_series(s: pd.Series, *, min_match_frac: float = 0.95) -> bool:
    if not (s.dtype == "object" or pd.api.types.is_string_dtype(s)):
        return False
    x = pd.Series(s, copy=False).astype("string").dropna()
    if x.empty:
        return False
    return float(x.str.strip().str.fullmatch(_UUID_RE, na=False).mean()) >= float(min_match_frac)


def _is_number_like_series(s: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(s) or pd.api.types.is_bool_dtype(s):
        return True
    if pd.api.types.is_datetime64_any_dtype(s) or pd.api.types.is_timedelta64_dtype(s):
        return True
    if s.dtype == "object":
        return bool(pd.to_numeric(s, errors="coerce").notna().mean() >= 0.95)
    return False


def _bounds_for_number_like(s: pd.Series, pad_frac: float, *, integer_like: bool = False) -> list[float]:
    x = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return [0.0, 1.0]
    vmin = float(np.min(x))
    vmax = float(np.max(x))
    span = vmax - vmin
    if span > 0:
        pad = pad_frac * span
    else:
        # Keep constant-column bounds exact unless user asked for non-zero padding.
        pad = max(abs(vmin) * pad_frac, 1.0) if pad_frac > 0 else 0.0
    lo = vmin - pad
    hi = vmax + pad
    if integer_like:
        return [int(np.floor(lo)), int(np.ceil(hi))]
    return [lo, hi]


def _binary_integer_domain_values(s: pd.Series) -> list[str] | None:
    x = pd.to_numeric(s, errors="coerce").to_numpy(dtype=float)
    x = x[np.isfinite(x)]
    if x.size == 0:
        return None
    ux = np.unique(x)
    if ux.size != 2 or not np.all(np.isclose(ux, np.round(ux), atol=1e-8)):
        return None
    return [str(v) for v in sorted([int(round(v)) for v in ux.tolist()])]


def _build_constraints(
    *,
    column_types: dict[str, str],
    public_categories: dict[str, list[str]],
    public_bounds: dict[str, list[float]],
    guid_like_columns: list[str],
    target_spec: dict[str, Any] | None,
) -> dict[str, Any]:
    column_constraints: dict[str, Any] = {}
    cross_column_constraints: list[dict[str, Any]] = []
    row_group_constraints: list[dict[str, Any]] = []
    for col, ctype in column_types.items():
        c: dict[str, Any] = {"type": ctype}
        if col in public_categories:
            c["allowed_values"] = public_categories[col]
        if col in public_bounds and len(public_bounds[col]) == 2:
            c["min"] = public_bounds[col][0]
            c["max"] = public_bounds[col][1]
        if col in guid_like_columns:
            c["semantic_role"] = "identifier"
        column_constraints[col] = c

    if isinstance(target_spec, dict) and str(target_spec.get("kind")) == "survival_pair":
        tcols = target_spec.get("targets")
        if isinstance(tcols, list) and len(tcols) >= 2:
            event_col = str(tcols[0])
            time_col = str(tcols[1])
            cross_column_constraints.append(
                {
                    "name": "survival_pair_definition",
                    "type": "survival_pair",
                    "event_col": event_col,
                    "time_col": time_col,
                    "event_allowed_values": [0, 1],
                    "time_min_exclusive": 0,
                }
            )
            ec = column_constraints.get(event_col, {"type": column_types.get(event_col, "categorical")})
            ec["allowed_values"] = ["0", "1"]
            column_constraints[event_col] = ec
            tc = column_constraints.get(time_col, {"type": column_types.get(time_col, "continuous")})
            tc["min_exclusive"] = 0
            column_constraints[time_col] = tc

    return {
        "column_constraints": column_constraints,
        "cross_column_constraints": cross_column_constraints,
        "row_group_constraints": row_group_constraints,
    }


def _merge_constraints(base: dict[str, Any], user: dict[str, Any]) -> dict[str, Any]:
    import copy
    out = copy.deepcopy(base)
    out.setdefault("column_constraints", {})
    out.setdefault("cross_column_constraints", [])
    out.setdefault("row_group_constraints", [])
    if isinstance(user.get("column_constraints"), dict):
        for col, rules in user["column_constraints"].items():
            if isinstance(rules, dict):
                if col not in out["column_constraints"]:
                    out["column_constraints"][col] = {}
                out["column_constraints"][col].update(rules)
    if isinstance(user.get("cross_column_constraints"), list):
        out["cross_column_constraints"].extend(copy.deepcopy(user["cross_column_constraints"]))
    if isinstance(user.get("row_group_constraints"), list):
        out["row_group_constraints"].extend(copy.deepcopy(user["row_group_constraints"]))
    return out


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True)
    ap.add_argument("--out", type=Path, required=True)
    ap.add_argument("--dataset-name", type=str, default=None)
    ap.add_argument("--target-col", type=str, default=None)
    ap.add_argument("--target-cols", type=str, default=None)
    ap.add_argument("--target-kind", type=str, default=None)
    ap.add_argument("--survival-event-col", type=str, default=None)
    ap.add_argument("--survival-time-col", type=str, default=None)
    ap.add_argument("--column-types", type=Path, default=None)
    ap.add_argument("--target-spec-file", type=Path, default=None)
    ap.add_argument("--constraints-file", type=Path, default=None)
    ap.add_argument("--delimiter", type=str, default="auto")
    ap.add_argument("--pad-frac", type=float, default=0.0)
    ap.add_argument(
        "--pad-frac-integer",
        type=float,
        default=None,
        help="Padding fraction for integer columns; falls back to --pad-frac if unset",
    )
    ap.add_argument(
        "--pad-frac-continuous",
        type=float,
        default=None,
        help="Padding fraction for continuous columns; falls back to --pad-frac if unset",
    )
    ap.add_argument("--infer-categories", action="store_true")
    ap.add_argument("--max-categories", type=int, default=200)
    ap.add_argument("--infer-binary-domain", action="store_true")
    ap.add_argument("--infer-datetimes", action="store_true")
    ap.add_argument("--datetime-min-parse-frac", type=float, default=0.95)
    ap.add_argument("--datetime-output-format", type=str, default="preserve")
    ap.add_argument("--guid-min-match-frac", type=float, default=0.95)
    ap.add_argument(
        "--no-publish-label-domain",
        action="store_true",
        help="Do not enumerate target column values into label_domain or public_categories",
    )
    ap.add_argument(
        "--redact-source-path",
        action="store_true",
        help="Write a placeholder instead of local source path in provenance.source_csv",
    )
    args = ap.parse_args()

    delimiter = _infer_csv_delimiter(args.data) if str(args.delimiter).strip().lower() == "auto" else str(args.delimiter)
    df = pd.read_csv(args.data, sep=delimiter, engine="python")
    cols = [str(c) for c in df.columns]
    target_col = args.target_col or _infer_target_col(cols)

    public_bounds: dict[str, list[float]] = {}
    public_categories: dict[str, list[str]] = {}
    missing_value_rates: dict[str, float] = {}
    column_types: dict[str, str] = {}
    datetime_spec: dict[str, dict[str, Any]] = {}
    guid_like_columns: list[str] = []
    pad_frac_global = float(args.pad_frac)
    pad_frac_integer = (
        float(args.pad_frac_integer) if args.pad_frac_integer is not None else pad_frac_global
    )
    pad_frac_continuous = (
        float(args.pad_frac_continuous)
        if args.pad_frac_continuous is not None
        else pad_frac_global
    )

    type_overrides: dict[str, Any] = {}
    if args.column_types is not None:
        type_overrides = json.loads(args.column_types.read_text())
        if not isinstance(type_overrides, dict):
            raise SystemExit("--column-types must be a JSON object")

    def _override_for(col: str) -> dict[str, Any] | None:
        if col not in type_overrides:
            return None
        v = type_overrides[col]
        if isinstance(v, str):
            return {"type": v}
        if isinstance(v, dict):
            return dict(v)
        raise SystemExit(f"--column-types[{col}] must be a string or object")

    for c in cols:
        s0 = df[c]
        missing_value_rates[c] = float(s0.isna().mean())

        if _is_guid_like_series(s0, min_match_frac=float(args.guid_min_match_frac)):
            column_types[c] = "categorical"
            guid_like_columns.append(c)
            continue

        s, dt_converted, dt_fmt_hint = _maybe_parse_datetime_like(
            s0, min_parse_frac=float(args.datetime_min_parse_frac)
        ) if bool(args.infer_datetimes) else (s0, False, None)

        ov = _override_for(c)
        if ov is not None:
            t = str(ov.get("type") or "").strip().lower()
            if t not in {"continuous", "integer", "categorical", "ordinal"}:
                raise SystemExit(f"--column-types[{c}].type invalid")
            column_types[c] = t
            dom = ov.get("domain")
            if t in {"categorical", "ordinal"} and dom is not None:
                if not isinstance(dom, list):
                    raise SystemExit(f"--column-types[{c}].domain must be list")
                public_categories[c] = [str(x) for x in dom]
            elif t in {"continuous", "integer"} and _is_number_like_series(s):
                this_pad = pad_frac_integer if t == "integer" else pad_frac_continuous
                public_bounds[c] = _bounds_for_number_like(
                    s,
                    this_pad,
                    integer_like=(t == "integer"),
                )
            if dt_converted:
                out_fmt = dt_fmt_hint if str(args.datetime_output_format).strip().lower() == "preserve" else str(args.datetime_output_format)
                datetime_spec[c] = {
                    "storage": "epoch_ns",
                    "output_format": out_fmt or "%Y-%m-%dT%H:%M:%S",
                    "timezone": "UTC",
                }
            continue

        if pd.api.types.is_bool_dtype(s0):
            column_types[c] = "ordinal"
            public_categories[c] = ["0", "1"]
        elif _is_number_like_series(s):
            if dt_converted:
                column_types[c] = "integer"
                out_fmt = dt_fmt_hint if str(args.datetime_output_format).strip().lower() == "preserve" else str(args.datetime_output_format)
                datetime_spec[c] = {
                    "storage": "epoch_ns",
                    "output_format": out_fmt or "%Y-%m-%dT%H:%M:%S",
                    "timezone": "UTC",
                }
                public_bounds[c] = _bounds_for_number_like(s, pad_frac_integer, integer_like=True)
            else:
                if pd.api.types.is_integer_dtype(s0):
                    column_types[c] = "integer"
                else:
                    x = pd.to_numeric(s, errors="coerce")
                    xn = x[np.isfinite(x)]
                    column_types[c] = "integer" if xn.size > 0 and np.all(np.isclose(xn, np.round(xn), atol=1e-8)) else "continuous"

                bin_dom = _binary_integer_domain_values(s) if bool(args.infer_binary_domain) else None
                if bin_dom is not None:
                    column_types[c] = "ordinal"
                    public_categories[c] = bin_dom
                else:
                    inferred_t = column_types[c]
                    this_pad = pad_frac_integer if inferred_t == "integer" else pad_frac_continuous
                    public_bounds[c] = _bounds_for_number_like(
                        s,
                        this_pad,
                        integer_like=(inferred_t == "integer"),
                    )
        else:
            column_types[c] = "categorical"
            if args.infer_categories:
                u = pd.Series(s, copy=False).astype("string").dropna().unique().tolist()
                u = [str(x) for x in u]
                if 0 < len(u) <= int(args.max_categories):
                    public_categories[c] = sorted(u)

    target_spec: dict[str, Any] | None = None
    if args.target_spec_file is not None:
        target_spec = json.loads(args.target_spec_file.read_text())
        if not isinstance(target_spec, dict):
            raise SystemExit("--target-spec-file must contain a JSON object")
    else:
        targets = _parse_csv_list(args.target_cols)
        if not targets and target_col:
            targets = [target_col]
        if args.survival_event_col and args.survival_time_col:
            targets = [args.survival_event_col, args.survival_time_col]
            target_kind = args.target_kind or "survival_pair"
        elif args.survival_event_col or args.survival_time_col:
            raise SystemExit("Both --survival-event-col and --survival-time-col must be provided together")
        else:
            target_kind = args.target_kind
        if targets:
            target_spec = {
                "targets": targets,
                "kind": target_kind or ("single" if len(targets) == 1 else "multi_target"),
                "dtypes": {t: _infer_target_dtype(df, t) for t in targets},
                "primary_target": target_col,
            }
            
    if target_spec is not None:
        tcols = target_spec.get("targets")
        if isinstance(tcols, list) and tcols:
            existing_dtypes = target_spec.get("dtypes") if isinstance(target_spec.get("dtypes"), dict) else {}
            normalized_dtypes: dict[str, str] = {}
            allowed = {"integer", "continuous", "categorical", "ordinal"}
            for t in [str(x) for x in tcols]:
                mapped = _target_dtype_from_column_type(column_types.get(t))
                if mapped is not None:
                    normalized_dtypes[t] = mapped
                elif isinstance(existing_dtypes.get(t), str):
                    raw = str(existing_dtypes[t]).strip().lower()
                    if raw not in allowed:
                        normalized_dtypes[t] = _infer_target_dtype(df, t)
                    else:
                        normalized_dtypes[t] = raw
                else:
                    normalized_dtypes[t] = _infer_target_dtype(df, t)
            target_spec["dtypes"] = normalized_dtypes

    label_domain: list[str] = []
    if target_col and target_col in df.columns and not args.no_publish_label_domain:
        if column_types.get(target_col) in {"categorical", "ordinal"}:
            u = pd.Series(df[target_col], copy=False).astype("string").dropna().unique().tolist()
            u_sorted = sorted([str(x) for x in u])
            if 0 < len(u_sorted) <= int(args.max_categories):
                label_domain = u_sorted
                public_categories[target_col] = label_domain

    if args.no_publish_label_domain:
        _targets_to_scrub: list[str] = []
        if target_spec is not None and isinstance(target_spec.get("targets"), list):
            _targets_to_scrub.extend([str(x) for x in target_spec["targets"]])
        elif target_col:
            _targets_to_scrub.append(target_col)
        for t in _targets_to_scrub:
            public_categories.pop(t, None)

    schema: dict[str, Any] = {
        "schema_version": SCHEMA_VERSION,
        "dataset": args.dataset_name or args.data.stem,
        "target_col": target_col,
        "label_domain": label_domain,
        "missing_value_rates": missing_value_rates,
        "public_bounds": public_bounds,
        "public_categories": public_categories,
        "column_types": column_types,
        "datetime_spec": datetime_spec,
        "provenance": {
            "generated_at_utc": datetime.now(timezone.utc).isoformat(),
            "source_csv": (
                "example_data_path_to_csv_file" if bool(args.redact_source_path) else str(args.data)
            ),
            "source_delimiter": delimiter,
            "pad_frac": pad_frac_global,
            "pad_frac_integer": pad_frac_integer,
            "pad_frac_continuous": pad_frac_continuous,
            "inferred_categories": bool(args.infer_categories),
            "max_categories": int(args.max_categories),
            "inferred_datetimes": bool(args.infer_datetimes),
            "datetime_min_parse_frac": float(args.datetime_min_parse_frac),
            "inferred_binary_domain": bool(args.infer_binary_domain),
            "guid_min_match_frac": float(args.guid_min_match_frac),
            "guid_like_columns": guid_like_columns,
            "datetime_output_format": str(args.datetime_output_format),
            "no_publish_label_domain": bool(args.no_publish_label_domain),
            "column_types_overrides": str(args.column_types) if args.column_types is not None else None,
        },
    }

    if target_spec is not None:
        schema["target_spec"] = target_spec

    constraints = _build_constraints(
        column_types=column_types,
        public_categories=public_categories,
        public_bounds=public_bounds,
        guid_like_columns=guid_like_columns,
        target_spec=target_spec,
    )
    if args.constraints_file is not None:
        user_constraints = json.loads(args.constraints_file.read_text())
        if not isinstance(user_constraints, dict):
            raise SystemExit("--constraints-file must contain a JSON object")
        constraints = _merge_constraints(constraints, user_constraints)
    schema["constraints"] = constraints

    args.out.parent.mkdir(parents=True, exist_ok=True)
    args.out.write_text(json.dumps(schema, indent=2) + "\n")
    print(f"Wrote schema to: {args.out}")


if __name__ == "__main__":
    main()
