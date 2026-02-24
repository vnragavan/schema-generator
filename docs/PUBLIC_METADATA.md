# Public Metadata

This document explains what the `public_bounds` and `public_categories` keys encode, how they are generated, and why they introduce privacy considerations when sharing schemas.

## What is `public_bounds`?
`public_bounds` is a dictionary mapping each numeric (integer or continuous) column to a two-element list `[min, max]`. It establishes the valid numerical range for that variable.

**How it is computed:**
By default, the script scans the dataset and records the exact, observed minimum and maximum values of the column.

**Privacy implications:**
Because the default behavior uses the exact data min/max mathematically, sharing `public_bounds` can directly reveal the most extreme individual values in the cohort (e.g., maximum age, lowest BMI, or highest laboratory value). If individuals can be re-identified via these extremes, this is a privacy leak.

## What is `public_categories`?
`public_categories` is a dictionary mapping each categorical or ordinal column to a sorted list of all unique non-null observed string values.

**Privacy implications:** 
This domain enumeration captures exact spellings, rare disease names, or individual string identifiers. If a variable contains granular or highly distinctive information, those strings are captured verbatim.

## Relationship to `label_domain`
`label_domain` simply duplicates the behavior of `public_categories` explicitly for the primary `target_col`. Unless disabled with the `--no-publish-label-domain` CLI flag, the distinct values of your prediction target will also be fully stringified into the schema.

## Recommended Mitigations
To maintain privacy when generating a schema for distribution in federated or open contexts, you should consistently apply these flags:

1. **Use padding:** Use the `--pad-frac`, `--pad-frac-integer`, or `--pad-frac-continuous` flags (e.g., `--pad-frac 0.05`). This numerically expands the minimum and maximum boundaries systematically outwards by a percentage of the total range across the dataset, masking the exact extreme individual's number.
2. **Cap unique domains:** Tune down the `--max-categories` flag (default 200). If a variable has thousands of unique strings, it's likely sensitive (e.g., identifiers, notes). Keeping the threshold low ensures distinct identifiers overflow the cap and won't get extracted into `public_categories`.
3. **Use `--redact-source-path`:** Always append this flag; otherwise your local machine's exact directory hierarchy gets stamped into the output `provenance.source_csv`.
4. **Human Review:** Manually review the output JSON. If a column's `public_categories` looks too granular (like detailed occupation titles), remove those keys from the schema before external distribution.
