# Changelog

All notable changes to the Schema Toolkit stand-alone component will be documented in this file.

## [1.3.0] - Unreleased
### Added
- `--no-publish-label-domain` flag added to manually suppress label string leaking during inference loop.
- Comprehensive bounding and null-value handling for GUID validation strings, explicit datetime preservation loops, and multi-target combinations.
- Comprehensive updates to constraints schema (`column_constraints`, `cross_column_constraints`, `row_group_constraints`).

### Changed
- Refactored `_merge_constraints` to perform deep structure duplications to prevent override bleed-throughs.
- `target_col` constraints correctly inherit the base loop types (bounds and ordinals are correctly extracted independent of labels escaping into domains). 

### Fixed
- Fixed bug where binary inference flag coerced successful datetime integers into string ordinals when they possessed 2 unique domain intervals.
- Fixed partial flag validation errors around `--survival-time-col` omitting `--survival-event-col`.

### Compatibility Note
Federated models requiring exact string `public_categories` outputs generated under versions `< 1.3.0` for boolean and identifier (GUIDs) inputs should re-generate the JSON artifact for strict backwards validation compatibilities, as exact integer inference types and list leakages have been corrected.
