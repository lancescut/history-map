# vEuropean — 欧洲史数据集

本目录承载 vEuropean 数据集的所有源数据 CSV / manifest / 边界 / 文档。与 `input/v03/` (中国) 和 `input/vIndian/` (印度) 同等地位，使用相同的 `v03-compatible-world-history` schema family（参见 `input/templates/`）。

## 时空范围

- **时间**：青铜时代到二战结束（-3000 → 1945）。冷战、欧盟、战后欧洲一体化暂不在本数据集范围内。
- **空间**：地中海（希腊、罗马、迦太基、腓尼基）、伊比利亚、意大利、法兰克/法国、德意志/神圣罗马、不列颠群岛、北欧、斯拉夫诸邦、巴尔干、俄罗斯，以及奥斯曼帝国在欧洲的部分。与欧洲史相关的近东、北非邻邦（拜占庭东方边境、十字军国家、奥斯曼扩张参照系）以 `neighbor_adm0` 形式纳入边界图层但不作为独立 polity。

## Schema 来源

所有 CSV 的字段顺序严格对齐 `input/templates/`。任何字段含义疑问以模板的 README 与字段说明为准；本数据集仅在文本层面填欧洲史，不引入新字段。

## 文件清单

| 文件 | 角色 | 模板 |
|---|---|---|
| `european_history_polities_master_vEuropean.csv` | 政权主表 | `world_history_polities_master_template.csv` |
| `european_history_polities_yearly_vEuropean.csv` | 年度展开（由 `generate_world_history_yearly.py` 生成） | `world_history_polities_yearly_template.csv` |
| `european_history_rulers_master_vEuropean.csv` | 君主主表 | `world_history_rulers_master_template.csv` |
| `capital_events_vEuropean.csv` | 首都事件 | `capital_events_template.csv` |
| `historical_events_vEuropean.csv` | 历史事件 | `historical_events_template.csv` |
| `historical_anecdotes_vEuropean.csv` | 典故/轶事/传说（含希腊罗马神话、北欧神话以 `anecdote_type=legend` 形式） | `historical_anecdotes_template.csv` |
| `historical_contexts_vEuropean.csv` | 时代背景说明 | （沿用 vIndian 字段顺序） |
| `strategic_locations_vEuropean.csv` | 战略位点（关隘、港口、宗教中心等） | `strategic_locations_template.csv` |
| `territory_overrides_vEuropean.csv` | 疆域覆盖（仅当自由文本无法解析时填） | `territory_overrides_template.csv` |
| `european_history_unresolved_or_disputed_vEuropean.csv` | 争议/未定 | `unresolved_or_disputed_template.csv` |
| `european_history_sources_vEuropean.csv` | 资料来源登记 | `sources_template.csv` |
| `european_history_validation_report_vEuropean.csv` | 校验报告（由 `validate_world_history_dataset.py` 写） | `validation_report_template.csv` |
| `story_presets_vEuropean.json` | 故事预设（演示预设：罗马帝国扩张、神圣罗马继承、宗教改革、拿破仑战争、两次世界大战等） | （沿用 vIndian 格式） |

## 行政区边界

参见 `admin_boundaries/README.md`。要点：
- 不存在统一的 `gbOpen/EUR` ISO，欧洲 ADM0 通过遍历约 50 个国家 ISO3 拉取 geoBoundaries `_simplified` 版本后聚合。
- 重点联邦/王国国家额外拉取 ADM1（DEU/ITA/ESP/GBR/RUS/AUT/CHE/POL/BEL），便于历史 polity 覆盖到州/region 粒度。
- 邻邦 ADM0 通过 `prepare_european_neighbor_boundaries.py` 单独拉取（地中海/黎凡特/北非）。

## 管道

```bash
npm run generate:data:europe
```

依次跑：年度展开 → schema 校验 → 行政区边界拉取 → 邻邦边界拉取 → 疆域 override 校验 → 公共数据构建。所有输出到 `public/data/vEuropean/`。

## 与 v03 / vIndian 的关系

- **共享前端**：在 UI 上通过顶部 Topbar 切换可见性；可单独显示、可与中国史/印度史并行显示。
- **配色**：vEuropean 使用冷色蓝绿色域（hue 200–330），与 vIndian 的暖色域（10–100 / 320–360）和 v03 的全色域明显区分。
- **dataset_id 标注**：每个 feature 在前端运行时注入 `dataset_id: "vEuropean"`，便于多源混合时区分。

## 编辑约束

- UTF-8 with BOM；逗号分隔；多值字段用 `|`。
- BCE 年份用负整数；不允许 year 0。
- 政权显示名 `polity_display_name` 使用中文译名；`polity_aliases` 保留原文（拉丁、希腊、德意、法兰西、西斯拉夫、东斯拉夫、希伯来、阿拉伯、土耳其等）至少一个原文别名。
- 神话/传说类故事（特洛伊战争、亚瑟王、北欧 Edda 等）入 `historical_anecdotes_vEuropean.csv`，`anecdote_type=legend`，**不**生成 polity yearly 行。
- 各种类型争议（神圣罗马帝国疆界、奥地利-匈牙利-波西米亚的多重计算、两次大战间的边境变动）入 `european_history_unresolved_or_disputed_vEuropean.csv`，不要在主表里默默选定一种说法。
