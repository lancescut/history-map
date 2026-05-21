# vIndian Web Playback Design and Acceptance Plan

## 目标

`input/vIndian` 继续作为独立数据包维护，不并入 `input/v03`。本轮开发目标是让 vIndian 导出的 `public/data/vIndian` 满足 Web 端播放契约：时间轴不 404、核心政权有可渲染近似疆域、战略地点 schema 与前端类型一致，生成和校验命令可以一键重复运行。

## 设计方案

### 1. 年份文件契约

- `dataset_manifest_vIndian.json` 的 `year_min/year_max` 定义可播放范围。
- `public/data/vIndian/metadata.json` 中 `year_count` 必须等于 `year_min..year_max` 去掉 year 0 后的真实文件数。
- 每个可播放年份都生成 `public/data/vIndian/years/{year}.json`；没有事件或政权的年份允许输出空数组，避免前端按年播放时 fetch 失败。
- BCE 年份继续使用负数，不产生 year 0。

### 2. 疆域渲染契约

- `territory_overrides_vIndian.csv` 的 `admin_ids` 优先使用稳定编码：
  - `IN-XX`：印度现代 ADM1 邦/联邦属地。
  - `IND`：全印度 ADM1 的便捷编码。
  - `PAK/BGD/NPL/AFG/BTN/LKA/MMR/CHN/IRN`：邻国 ADM0。
- 对没有 override 的核心政权，生成器从 `modern_admin_units_raw` 做保守解析，例如 `India Punjab/Haryana`、`Pakistan|Bangladesh`、`Jammu and Kashmir`。
- 解析失败的候选土邦不强行渲染，继续保留 `needs_geography_review` 数据状态。
- 输出仍为近似 MultiPolygon，不重建南亚历史边界。

### 3. 战略地点契约

- `strategic_locations_vIndian.csv` 是唯一维护入口。
- 只有 `review_status=verified` 且有经纬度的地点进入公开 JSON/GeoJSON。
- 公开 JSON 必须完整匹配前端 `StrategicLocation` 类型：`aliases`、`icon_key`、`start_year/end_year`、`active_years`、`active_year_ranges`、`strategic_summary`、`default_visible` 等字段都必须存在。
- 默认显示规则：verified 且 `importance_level <= 2`；其余可通过后续筛选/缩放策略扩展。

### 4. 搜索契约

- `alias_index.json` 的每条记录必须包含 `alias`、`normalized`、`label`、`entity_type`、`entity_id`。
- 搜索覆盖 polity、ruler、capital、strategic_location；战略地点结果保留经纬度，便于前端 fly-to。

### 5. 生成链契约

- `npm run generate:data:india` 必须顺序执行：
  1. 生成年度展开表。
  2. 校验 vIndian CSV。
  3. 准备印度 ADM1 和邻国 ADM0 边界。
  4. 校验 territory overrides。
  5. 生成 public vIndian JSON/GeoJSON。
- `npm run validate:data` 同时覆盖 v03 既有校验和 vIndian 数据校验。

## 验收方案

### 命令验收

- `npm run generate:data:india` 成功，且输出 year files 数量等于 metadata 的 `year_count`。
- `python3 scripts/validate_world_history_dataset.py --dataset vIndian` 成功。
- `python3 scripts/validate_territory_overrides_vindian.py` 成功且无自由文本 only 的渲染阻断项。
- `npm run build` 成功。

### 数据验收

- `metadata.year_min=-7000`、`metadata.year_max=1990`、`metadata.has_year_zero=false`。
- `public/data/vIndian/years/-6999.json`、`-3300.json`、`-321.json`、`1947.json`、`1950.json`、`1990.json` 均存在。
- `public/data/vIndian/years/0.json` 不存在。
- `territory_polity_count` 明显高于只靠 override 的 6 条；核心样例孔雀、笈多、德里苏丹、莫卧儿、英属印度、印度共和国都有 territory feature。
- `strategic_locations.json` 中每个地点都有 `icon_key`、`active_years`、`active_year_ranges`、`strategic_summary`、`default_visible`。
- `alias_index.json` 不存在缺少 `normalized` 的 entry。

### Web 烟测

- 启动 `npm run dev`，打开本地页面。
- 在数据源选择中启用印度史，切到 BCE 与现代年份，页面不出现 year-data 404。
- 地图能显示印度史政权列表、事件/典故流和战略地点；搜索 `Maurya`、`Pataliputra`、`Bodh Gaya` 能返回结果。

## 本轮边界

- 不扩充古印度史实条目数量。
- 不制作南亚历史边界 GeoJSON。
- 不改 v03 中国史 schema。
- 对 `needs_geography_review` 的大量土邦只保留数据，不在本轮硬编码位置。
