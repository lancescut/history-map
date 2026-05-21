# v03-compatible world history templates

These templates preserve the v03 CSV column order while making the field
semantics reusable for India, Egypt, Babylon, Europe, and later datasets.

Rules:

- Keep UTF-8 with BOM for CSV files, comma delimiters, and `|` for multi-value fields.
- BCE years are negative integers and year 0 is forbidden.
- `modern_admin_units_raw` is a modern geographic approximation, not a historical boundary claim.
- East Asian ruler-name columns may stay empty when they do not apply.
- Uncertain chronologies, legendary king lists, and territorial disputes must be recorded in the issues table.
- Epic, Puranic, dynastic-origin, and other mythic traditions belong in `mythological_timeline_template.csv`, not in historical polity yearly rows.
- Dataset-specific file names are declared in `dataset_manifest_*.json`; validators compare each dataset file to these templates.
