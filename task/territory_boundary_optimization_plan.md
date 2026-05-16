# 疆域边界优化设计方案：从矩形近似升级为真实现代省级边界拼合

创建日期：2026-05-15  
适用范围：v1 年度疆域演示系统  
结论：当前矩形边界只能作为 pipeline 占位 fixture，不能作为用户可接受的 v1 效果。v1 应改为基于真实现代省级行政边界的拼合疆域，仍明确标注“现代行政区近似，非历史精确边界”。

## 1. 当前问题

当前 `input/v03/modern_admin_boundaries_simplified.geojson` 每个省级单位都是手工 bbox 矩形。`scripts/generate_public_data.py` 虽然已经能把多个现代行政区合并为政权疆域，但合并的基础几何是矩形，所以用户看到的是大片方块，而不是接近中国现行省市划分的区域边界。

这不是样式问题，而是数据基底问题。继续调 MapLibre fill、opacity、outline 都无法解决“正方形疆域”的核心体验缺陷。

## 2. 数据源选择

### P0 推荐：geoBoundaries gbOpen ADM1

优先使用 geoBoundaries 的 `CHN ADM1 gbOpen` 作为离线提交的真实省级边界基线。实际固定的 geoBoundaries API metadata 显示该 CHN ADM1 边界记录为 `Public Domain`，来源为 `geoBoundaries / Wikimedia Commons`；应用仍在图例中保留边界源署名，便于追溯 [geoBoundaries](https://www.geoboundaries.org/)。

选择原因：
- 真实行政边界，不是 bbox。
- WGS84/GeoJSON 工作流友好，适合 MapLibre。
- 授权清楚，可离线提交到仓库，但必须在应用图例或数据说明中保留 attribution。
- 与现有“现代行政区近似”口径一致，不追求历史精确边界。

### P1 备选：Natural Earth 10m Admin-1

Natural Earth 是公共领域地图数据，适合低风险分发；其 Admin-1 主题覆盖国家内部一级行政区边界，但 Natural Earth 110m 页面也提示更详细国家内部一级区划应查看 10m admin-1，不能把 110m 版本当作中国省级边界主数据 [Natural Earth](https://www.naturalearthdata.com/downloads/110m-cultural-vectors/110m-admin-1-states-provinces/)。

使用策略：只作为 geoBoundaries 不可用时的 fallback，不作为首选。

### P1 备选但需授权确认：GeoJSON.cn / DataV 类国内数据

GeoJSON.cn 提供中国省市县三级 GeoJSON/TopoJSON 数据接口，并说明 1.6.0 起数据源为腾讯地图 API、坐标系为 GCJ-02，之前版本为 WGS84 [GeoJSON.cn](https://geojson.cn/data/atlas/china)。这类数据在视觉上更贴近国内互联网地图口径，但存在两个实现风险：

- 坐标系：GCJ-02 不能直接和当前 WGS84 都城坐标混用，否则 marker 和 polygon 会有偏移。
- 授权：需要明确是否允许离线提交和产品再分发，不能只因为 API 可访问就直接纳入仓库。

使用策略：如果后续产品明确要国内地图口径，可作为 P1 专项，但必须增加坐标转换、授权记录和数据来源审计。

### 不推荐作为 v1 主源

GADM 不适合作为可提交的 v1 主数据，因为其官方 license 明确写明可免费用于学术和非商业用途，但未经许可不允许再分发或商业使用 [GADM license](https://gadm.org/license.html)。

OpenStreetMap 边界数据可用但默认受 ODbL 约束，应用内打包和再分发需要严格处理 attribution 与数据库派生义务 [OpenStreetMap export](https://www.openstreetmap.org/export)。OSM 的行政边界建模也依赖 `boundary=administrative` 和 `admin_level` 体系，适合后续精细数据工程，不适合作为 v1 快速稳定主源 [OSM wiki](https://wiki.openstreetmap.org/wiki/Tag%3Aboundary%3Dadministrative?uselang=en)。

Apache ECharts 当前官方不再提供地图数据下载，因此不能把 ECharts 当作地图数据来源 [ECharts maps](https://echarts.apache.org/en/download-map.html)。

## 3. 新数据目录与文件

新增目录：

```text
input/v03/admin_boundaries/
  china_adm1_geoboundaries_raw.geojson
  china_adm1_normalized.geojson
  admin_boundary_source_manifest.json
  README.md
```

保留当前矩形文件但降级为测试 fixture：

```text
input/v03/fixtures/modern_admin_boundaries_rect_fixture.geojson
```

正式 pipeline 读取：

```text
input/v03/admin_boundaries/china_adm1_normalized.geojson
```

标准 Feature properties：

```json
{
  "admin_id": "CN-BJ",
  "name": "北京市",
  "aliases": "北京|京",
  "admin_level": "province",
  "source": "geoBoundaries",
  "source_release": "gbOpen",
  "source_license": "Public Domain",
  "source_url": "https://www.geoboundaries.org/",
  "crs": "WGS84"
}
```

## 4. 新增预处理 Pipeline

### 4.1 边界获取与固定版本

新增脚本：

```text
scripts/prepare_admin_boundaries.py
```

职责：
- 从本地 raw GeoJSON 读取真实省级边界，不在应用运行时请求远程服务。
- 统一属性名为 `admin_id/name/aliases/admin_level/source/license/crs`。
- 输出 `china_adm1_normalized.geojson`。
- 生成 `admin_boundary_source_manifest.json`，记录 source URL、license、下载日期、sha256、feature_count。
- 如果 source feature 数、sha256、字段 schema 变化，CI 或 `npm run validate:data` 必须失败。

### 4.2 几何清洗与简化

新增可重复构建步骤：

```bash
mapshaper input.geojson -clean -simplify weighted 12% keep-shapes -o precision=0.0001 output.geojson
```

Mapshaper CLI 支持读取 GeoJSON/Shapefile、简化并输出 GeoJSON，文档示例也说明可用 `-simplify` 和 `precision` 控制文件体积与坐标精度 [mapshaper docs](https://mapshaper.org/docs/essentials/command-line.html)。

验收规则：
- 禁止 bbox 矩形作为正式边界：每个省级 feature 外环点数应大于阈值，例如 `>= 20`。
- 所有 geometry 必须是 `Polygon` 或 `MultiPolygon`。
- 所有坐标必须在合理范围内。
- 坐标系必须是 WGS84。若使用 GCJ-02 数据，必须先转换并标注转换来源。

### 4.3 政权疆域拼合

当前 `build_polity_territories()` 逻辑保留，但改造三点：

1. 从 `china_adm1_normalized.geojson` 读取真实省级 polygon。
2. 将当前写死的 `TERRITORY_OVERRIDES` 迁移到 CSV：

```text
input/v03/territory_overrides_v03.csv
```

字段：

```text
polity_id,polity_name,admin_ids,valid_from_year,valid_to_year,match_source,confidence_score,note,source_titles,source_raw
```

3. 对每个政权输出两份 geometry：

```text
public/data/v03/territories/approx_polities.geojson
public/data/v03/territories/admin_units_by_polity.geojson
```

`approx_polities.geojson` 用于政权整体 fill，尽量 dissolve 省界内部线；`admin_units_by_polity.geojson` 用于调试和详情面板展示“由哪些现代省级单位拼合而来”。

### 4.4 面积与中心点计算

当前 bbox 面积估算必须废弃。改为真实 polygon 面积计算。Turf `area` 明确接受 GeoJSON Polygon/FeatureCollection，并返回平方米 [Turf area](https://turfjs.org/docs/api/area)。实现上建议新增 Node 脚本或引入轻量 JS preprocessing：

```text
scripts/compute_territory_metrics.mjs
```

输出：
- `approx_area_km2`
- `centroid`
- `bbox`
- `geometry_vertex_count`
- `geometry_precision`

## 5. 匹配规则优化

当前 substring 匹配容易过宽。新版规则：

1. 优先匹配 `territory_overrides_v03.csv` 的 `admin_ids`。
2. 其次解析 `modern_admin_units_raw`，但必须按行政区词典 token 匹配，不允许任意短 substring 命中。
3. 对“部分、一带、东部、南部、活动范围”等词降置信度。
4. 对明确省级名称命中给 `matched`，对区域描述给 `matched_low_confidence`，对无可靠匹配给 `missing`。
5. 每条匹配都写入 `territory_match_report.csv`，记录 `matched_admin_ids`、`unmatched_tokens`、`match_source`、`confidence_note`。

## 6. 地图与 UI 优化

地图层级：

```text
base map
modern-admin-reference-outline   低透明现代省界参考线，可开关
territory-fill-previous          年份切换淡出
territory-fill-current           当前年份真实边界拼合面
territory-outline-current        政权外轮廓
territory-labels                 LOD 标签
capital-markers
migration-lines
```

视觉原则：
- 默认不展示省级内部线，避免用户误以为政权内部存在现代省界。
- 开启“现代行政区参考线”时，才显示淡灰省界。
- 图例文案改为：“疆域由现代省级行政边界拼合，非历史精确边界。”
- 详情面板展示“拼合来源：河北省、山西省、河南省……”和 `match_confidence`。
- 若 geometry 来自 GCJ-02 转换，详情中必须标注“坐标源经转换”。

## 7. 验收标准

数据验收：
- `input/v03/admin_boundaries/china_adm1_normalized.geojson` 存在。
- 正式边界 feature 不得是四点矩形。
- `public/data/v03/territories/approx_polities.geojson` 中所有有疆域政权使用真实 polygon 或 multipolygon。
- `territory_match_report.csv` 包含 source、license、matched_admin_ids、confidence_note。
- `metadata.json` 增加 `admin_boundary_source`、`admin_boundary_license`、`admin_boundary_feature_count`、`territory_geometry_quality`。

视觉验收：
- 前 688 年不再显示矩形块，所有疆域边缘应接近现代省级边界形状。
- 1421 年明朝不再由正方形拼接，而是由真实省级边界拼合成面。
- 迁都 marker、迁都线、年度列表、政权详情仍同步更新。
- 图例和详情必须持续声明非历史精确边界。

回归验收：
- `npm run generate:data` 仍生成 2,955 年度文件。
- `npm run validate:data` 通过。
- `npm run build` 通过。
- Playwright smoke test 覆盖：首屏真实 polygon、1421 年迁都、polygon 点击、搜索“北京”、疆域缺失筛选。

## 8. 实施任务拆分

P0-1 数据源替换：
- 下载并固定 geoBoundaries CHN ADM1 gbOpen raw GeoJSON。
- 新增 `admin_boundary_source_manifest.json`。
- 编写 `prepare_admin_boundaries.py`，输出 normalized GeoJSON。

P0-2 Pipeline 改造：
- 将 `generate_public_data.py` 改为读取 normalized 真实边界。
- 将 `TERRITORY_OVERRIDES` 迁移到 `territory_overrides_v03.csv`。
- 将 bbox 面积替换为 polygon 面积。
- 生成 `admin_units_by_polity.geojson`。

P0-3 UI 改造：
- 新增现代省界参考线图层开关。
- 更新图例和详情面板口径。
- 优化 labels 和 outline，避免真实边界在 54 政权并存时过度糊成一片。

P0-4 验证：
- 增加“禁止矩形正式边界”校验。
- 增加 source/license/sha256 校验。
- Playwright 截图对比前 688 年与 1421 年。

## 9. 风险与决策点

需要产品确认的决策：
- v1 是否只覆盖中国大陆省级行政区，还是要包含港澳台和南海诸岛口径。
- attribution 展示位置：建议放在地图图例底部和“数据来源”面板。
- 是否接受 geoBoundaries 的全球通用边界口径，或必须改用国内地图数据口径。

建议决策：
- v1 先采用 geoBoundaries gbOpen ADM1，因为授权、离线提交、WGS84、工程稳定性最平衡。
- 国内 GeoJSON/GCJ-02 数据作为 P1 备选，不进入 P0，除非先补齐授权与坐标转换验收。
