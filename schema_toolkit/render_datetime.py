#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from pathlib import Path

import pandas as pd


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--data", type=Path, required=True, help="Input CSV with epoch-ns datetime columns")
    ap.add_argument("--schema", type=Path, required=True, help="Schema JSON containing datetime_spec")
    ap.add_argument("--out", type=Path, required=True, help="Output CSV path")
    ap.add_argument(
        "--keep-original",
        action="store_true",
        help="Keep epoch-ns source column and write rendered values to <col>__rendered",
    )
    args = ap.parse_args()

    df = pd.read_csv(args.data)
    schema = json.loads(args.schema.read_text())
    dspec = schema.get("datetime_spec", {}) if isinstance(schema, dict) else {}
    if not isinstance(dspec, dict) or not dspec:
        print("Note: Schema has no datetime_spec; cleanly exiting render process.")
        return

    out_df = df.copy()
    for col, meta in dspec.items():
        if col not in out_df.columns:
            continue
        fmt = "%Y-%m-%dT%H:%M:%S"
        if isinstance(meta, dict):
            maybe_fmt = meta.get("output_format")
            if isinstance(maybe_fmt, str) and maybe_fmt.strip():
                fmt = maybe_fmt

        vals = pd.to_numeric(out_df[col], errors="coerce")
        dt = pd.to_datetime(vals, unit="ns", utc=True, errors="coerce")
        rendered = dt.dt.strftime(fmt).where(dt.notna(), pd.NA)
        if args.keep_original:
            out_df[f"{col}__rendered"] = rendered
        else:
            out_df[col] = rendered

    args.out.parent.mkdir(parents=True, exist_ok=True)
    out_df.to_csv(args.out, index=False)
    print(f"Wrote rendered CSV: {args.out}")


if __name__ == "__main__":
    main()
