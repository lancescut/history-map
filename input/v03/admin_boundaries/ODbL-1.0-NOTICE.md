# ODbL 1.0 Notice for v03 County Boundary Data

This project includes derived county-level boundary data from geoBoundaries `gbOpen/CHN/ADM3`.

- Source: geoBoundaries
- Source layer: CHN ADM3 GeoJSON
- Source metadata: https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM3/
- Download URL: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM3/geoBoundaries-CHN-ADM3.geojson
- License: Open Data Commons Open Database License 1.0
- License text: https://opendatacommons.org/licenses/odbl/1-0/
- Attribution: geoBoundaries / Lee Beryman, OpenStreetMap

Derived files in this repository include:

- `input/v03/admin_boundaries/china_adm3_geoboundaries_raw.geojson`
- `input/v03/admin_boundaries/china_adm3_normalized.geojson`
- `public/data/v03/territories/county_units.geojson`
- `public/data/v03/territories/polity_county_index.json`

The normalized data adds stable project IDs, parent ADM1 references, bbox/centroid metadata, coordinate counts, and v03 indexing fields. Boundaries are modern administrative references and are not historical exact territory boundaries. No endorsement by geoBoundaries or its upstream sources is implied.
