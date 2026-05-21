# ODbL 1.0 Notice for vIndian Boundary Data

This project includes derived state-level and district-level boundary data from
geoBoundaries `gbOpen/IND/ADM1` and `gbOpen/IND/ADM2`.

- Source: geoBoundaries
- ADM1 layer: IND ADM1
- ADM2 layer: IND ADM2
- ADM1 metadata: https://www.geoboundaries.org/api/current/gbOpen/IND/ADM1/
- ADM2 metadata: https://www.geoboundaries.org/api/current/gbOpen/IND/ADM2/
- ADM2 download URL: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/IND/ADM2/geoBoundaries-IND-ADM2_simplified.geojson
- License: Open Data Commons Open Database License 1.0
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: geoBoundaries / Pathways Data Pvt. Ltd., lgdirectory.gov.in

Derived files in this repository include:

- `input/vIndian/admin_boundaries/india_adm1_geoboundaries_raw.geojson`
- `input/vIndian/admin_boundaries/india_adm1_normalized.geojson`
- `input/vIndian/admin_boundaries/india_adm2_geoboundaries_raw.geojson`
- `input/vIndian/admin_boundaries/india_adm2_normalized.geojson`
- `public/data/vIndian/territories/county_units.geojson` (Phase 1.6+ when generator wired)
- `public/data/vIndian/territories/polity_county_index.json` (Phase 1.6+)

The normalized data adds stable project IDs, parent ADM1 references, bbox/centroid metadata,
coordinate counts, and vIndian indexing fields. Boundaries are modern administrative references
and are NOT historical exact territory boundaries. No endorsement by geoBoundaries or its
upstream sources is implied.
