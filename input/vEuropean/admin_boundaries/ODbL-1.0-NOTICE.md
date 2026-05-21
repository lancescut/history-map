# ODbL 1.0 Notice for vEuropean Boundary Data

This project includes derived country-level (ADM0) and select first-level
administrative (ADM1) boundary data from geoBoundaries `gbOpen` for 47
European countries and 10 federation-level ADM1 layers.

- Source: geoBoundaries (https://www.geoboundaries.org/)
- Pinned commit: 9469f09
- License: Open Data Commons Open Database License 1.0
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: geoBoundaries

Derived files in this repository include:

- `input/vEuropean/admin_boundaries/eu_adm0_normalized.geojson`
- `input/vEuropean/admin_boundaries/{iso3}_adm1_normalized.geojson` (per federation)
- `input/vEuropean/admin_boundaries/raw/{iso3}_adm0.geojson` (cached downloads)
- `input/vEuropean/admin_boundaries/raw/{iso3}_adm1.geojson` (cached downloads)

The normalized data adds stable project IDs (ISO3 for ADM0, ISO 3166-2 codes
or fallback hashes for ADM1), Chinese display names, bbox/centroid metadata,
coordinate counts, and 5-decimal coordinate rounding. Boundaries are MODERN
administrative references, not historical exact territory boundaries. No
endorsement by geoBoundaries or its upstream sources is implied.
