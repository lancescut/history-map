# 中国历代政权年度数据 v03

本目录是 v03 规范化数据集。v03 的原则是：先维护“政权级事实源”和“君主级事实源”，再从这两张标准表自动生成年度展开主表，避免 v02 中出现的“起止年份已校正，但年度行没有同步删除或补齐”的问题。

## 文件一览

### 1. `chinese_history_polities_master_v03.csv`

政权级标准表。每个政权一个 `polity_id`，记录政权名称、异名、起止年份、版图字段、都城、族属、创建者、灭亡/继承关系、史料出处、置信度、以及从 v02 合并来的上下文。

适合用来回答：

- 某个国家或政权到底从哪一年到哪一年？
- 这个起止年份依据是什么？
- 这个政权有哪些异名或简繁写法？
- 历史地理与现代行政区怎么对应？

### 1.1 `territory_zones_v03.csv`

疆域控制性质标准表。凡是一个政权的范围同时包含“实控疆域”和“影响区/都护/羁縻/名义或阶段性控制”等不同性质，必须在本表拆成 zone 维护，不能只写在自由文本里。

固定字段：

- `zone_id`: zone 主键，必须唯一。
- `polity_id` / `polity_name`: 关联政权。
- `control_type`: 只允许 `direct` 或 `influence`。
- `zone_start_year` / `zone_end_year`: zone 有效年份，不得包含 year 0。
- `zone_geography_raw` / `zone_modern_admin_units_raw`: 历史地理描述与现代行政区近似文本。
- `source_titles` / `source_urls` / `source_raw`: 可审计来源。
- `confidence_score` / `note`: 置信度与口径说明。

渲染标准：

- `direct` 表示实控、郡县、核心统治区，地图使用政权色实心填充。
- `influence` 表示都护、羁縻、册封、藩属、阶段性控制、势力影响区、非整国控制，地图使用同政权颜色的虚线斜纹阴影。
- 没有本表记录的旧政权由生成脚本自动视为一个 `direct` zone，以保持向后兼容。

### 2. `chinese_history_rulers_master_v03.csv`

君主级标准表。每个君主一个 `ruler_id`，通过 `polity_id` 关联到政权，记录君主名称、庙号、谥号、本名、实际统治起止年、年号、出处和置信度。

适合用来回答：

- 某个政权有哪些君主？
- 某位君主实际统治年份是多少？
- 该君主信息来自哪个来源？

### 3. `chinese_history_polities_yearly_v03.csv`

年度展开主表，也是地图、时间轴、年度查询最应该使用的表。它由政权标准表和君主标准表重新生成，不再直接继承 v02 的旧年度行。

查看方法：

- 查某一年有哪些政权：筛选 `year`。
- 查某个政权完整存在期：筛选 `polity_id` 或 `polity_name`。
- 查某年某国的君主：筛选 `year` + `polity_id`，再看 `ruler_name`。
- `row_granularity = year_polity_ruler` 表示该年匹配到君主。
- `row_granularity = year_polity_unmatched_ruler` 表示该政权这一年存在，但暂未匹配到可解析君主年表；君主字段留空，不代表国家不存在。

### 4. `chinese_history_unresolved_or_disputed_v03.csv`

争议、未定与口径说明表。这里记录不能强行伪造成确定事实的内容，例如：

- 起止年份缺失或只能部分确定。
- v02 中被合并的简繁/异体/重复上下文。
- 后燕、清朝、元朝、西夏等存在不同纪年口径的记录。

查看方法：当你在主表里看到某个年份或政权和其他资料不一致，先到这张表按 `polity_id` 或 `polity_name` 查原因。

### 5. `chinese_history_validation_report_v03.csv`

生成后的质量检查表。它不是历史资料，而是数据工程质检结果。

重点看：

- `year_within_polity_range`: 每一行 `year` 是否都在政权起止范围内。
- `polity_year_completeness`: 每个可解析起止范围的政权，存在期内是否每一年都有至少一行。
- `partial_polity_boundaries`: 哪些政权仍缺少完整起止年份。
- `yearly_polity_id_join` / `yearly_ruler_id_join`: 主表能否正确关联回标准表。

只要 `FAIL` 为 0，说明年度展开结构是干净的；`WARN` 表示需要人工保留说明，但不是生成失败。

### 6. `RELEASE_NOTES.md`

v03 数据集的发布与变更记录。每次修改 `input/v03` 源数据、生成报告，或重新生成 `public/data/v03` 公开产物，都应在这里追加说明，记录变更原因、涉及文件、生成影响和校验结果。

## 本次生成规模

- 政权标准项：209 条
- 君主标准项：1153 条
- 年度主表行：40077 行
- 争议/未定说明：63 条
- 校验项：9 条

## 与 v02 的关系

v02 是人工校正后的大表，但它把政权元数据重复复制到大量年度行里，所以容易出现局部更新后年度行不同步的问题。v03 把 v02 拆成标准表，再重新生成年度主表。

因此，v03 的行数、`row_id` 和部分重复政权的显示方式会和 v02 不同。这是预期变化。需要跨表关联时，请优先使用 `polity_id` 和 `ruler_id`，不要依赖行号。
