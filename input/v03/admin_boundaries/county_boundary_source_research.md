# v03 县级边界数据源研究

## 结论

本项目采用 geoBoundaries `gbOpen/CHN/ADM3` simplified GeoJSON 作为 v03 县级现代行政边界源。

## 选择理由

- geoBoundaries 提供固定 API 元数据与 WGS84 GeoJSON，当前元数据记录为 2867 个 ADM3 单元；本次下载文件实际包含 2864 个 feature，差异已写入 manifest。
- geoBoundaries ADM3 当前许可为 `Open Data Commons Open Database License 1.0`，可随公开仓库分发派生数据，但必须保留 ODbL 署名、许可与派生说明。
- GADM 许可不适合作为本项目公开仓库的再分发首选源。
- GeoJSON.cn 县级离线数据需要授权；且 1.6+ 数据为 GCJ-02，不作为当前公开 WGS84 数据流水线源。

## 数据口径

- 当前县级边界是现代行政区近似层，不是历史疆域实测层。
- v03 继续保留 ADM1 摘要匹配，用来兼容旧字段 `matched_admin_ids` / `matched_admin_units`。
- 新增 ADM3 县级事实层与 `polity_county_index.json`，年度记录只保存 `territory.county_index_ref` 和统计字段。
- geoBoundaries 的 CHN ADM3 名称以来源 `shapeName` 为准；中文县级别名后续可通过授权地名表或人工别名表追加，不影响县级索引稳定性。

## 来源

- API metadata: https://www.geoboundaries.org/api/current/gbOpen/CHN/ADM3/
- Download URL: https://github.com/wmgeolab/geoBoundaries/raw/9469f09/releaseData/gbOpen/CHN/ADM3/geoBoundaries-CHN-ADM3.geojson
- Note: 当前 API 的 GeoJSON 下载文件返回 feature 数少于 `admUnitCount`；清洗脚本不伪造缺失 feature，manifest 同时记录 metadata count、actual count 与 discrepancy。
- License: Open Data Commons Open Database License 1.0
- Source attribution: geoBoundaries / Lee Beryman, OpenStreetMap
- Build date: Dec 12, 2023
