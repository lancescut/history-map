# vEuropean Admin Boundaries

本目录承载 vEuropean 数据集使用的现代行政区边界，作为历史政权疆域的近似几何源。

## 与 v03 / vIndian 的关键差异

- **v03**：geoBoundaries `gbOpen/CHN/ADM1` + `ADM3` 一次性拉取，单 ISO。
- **vIndian**：geoBoundaries `gbOpen/IND/ADM1` + `ADM2`，单 ISO。
- **vEuropean**：**没有统一的 `EUR` ISO**。`prepare_european_admin_boundaries.py` 遍历约 50 个欧洲国家 ISO3，拉取每个的 `_simplified.geojson`，聚合为单个 `eu_adm0_normalized.geojson`。对历史上长期为联邦 / 多王国合并的国家，额外拉取 `ADM1_simplified`，存为 `{ISO3}_adm1_normalized.geojson`。

## 数据源

- geoBoundaries gbOpen 项目，pinned commit `9469f09`（与 v03/vIndian 同步）。
- 每个国家的 ADM0 走 `geoBoundaries-{ISO3}-ADM0_simplified.geojson`。
- 重点联邦的 ADM1 走 `geoBoundaries-{ISO3}-ADM1_simplified.geojson`。
- 邻邦 ADM0 通过 Natural Earth 110m `ne_110m_admin_0_countries`，由 `prepare_european_neighbor_boundaries.py` 单独拉取。

## ADM0 国家清单（约 50 国）

| ISO3 | 国家 | 备注 |
|---|---|---|
| ALB | 阿尔巴尼亚 |  |
| AND | 安道尔 | 微型国 |
| AUT | 奥地利 | 含 ADM1（Bundesländer） |
| BEL | 比利时 | 含 ADM1（provinces） |
| BGR | 保加利亚 |  |
| BIH | 波斯尼亚和黑塞哥维那 |  |
| BLR | 白俄罗斯 |  |
| CHE | 瑞士 | 含 ADM1（Kantone） |
| CYP | 塞浦路斯 |  |
| CZE | 捷克 |  |
| DEU | 德国 | 含 ADM1（Länder） |
| DNK | 丹麦 |  |
| ESP | 西班牙 | 含 ADM1（comunidades autónomas） |
| EST | 爱沙尼亚 |  |
| FIN | 芬兰 |  |
| FRA | 法国 |  |
| GBR | 英国 | 含 ADM1（England/Scotland/Wales/N.Ireland 四国） |
| GRC | 希腊 |  |
| HRV | 克罗地亚 |  |
| HUN | 匈牙利 |  |
| IRL | 爱尔兰 |  |
| ISL | 冰岛 |  |
| ITA | 意大利 | 含 ADM1（regioni） |
| KOS | 科索沃 | 部分认可 |
| LIE | 列支敦士登 | 微型国 |
| LTU | 立陶宛 |  |
| LUX | 卢森堡 |  |
| LVA | 拉脱维亚 |  |
| MCO | 摩纳哥 | 微型国 |
| MDA | 摩尔多瓦 |  |
| MKD | 北马其顿 |  |
| MLT | 马耳他 |  |
| MNE | 黑山 |  |
| NLD | 荷兰 |  |
| NOR | 挪威 |  |
| POL | 波兰 | 含 ADM1（voivodeships） |
| PRT | 葡萄牙 |  |
| ROU | 罗马尼亚 |  |
| RUS | 俄罗斯 | 含 ADM1（federal subjects，按需选用） |
| SMR | 圣马力诺 | 微型国 |
| SRB | 塞尔维亚 |  |
| SVK | 斯洛伐克 |  |
| SVN | 斯洛文尼亚 |  |
| SWE | 瑞典 |  |
| TUR | 土耳其 | 仅取欧洲色雷斯部分？暂全国，后期可裁切 |
| UKR | 乌克兰 |  |
| VAT | 梵蒂冈 | 微型国 |

## Admin ID 命名

- ADM0 国家：直接用 `{ISO3}`，例如 `FRA`、`GBR`、`DEU`、`POL`。
- 重点联邦 ADM1：使用 `{ISO2}-{regionCode}`，例如 `DE-BY`（Bayern）、`IT-25`（Lombardy）、`ES-CT`（Catalonia）、`GB-SCT`（Scotland）、`AT-9`（Wien）、`CH-ZH`（Zürich）、`PL-MZ`（Mazowieckie）、`BE-VLG`（Flanders）、`RU-MOW`（Moscow oblast）。
- `territory_overrides_vEuropean.csv` 的 `admin_ids` 字段以 `|` 分隔，可以混用 ADM0 与 ADM1，例如 `FRA|DE-BY|DE-BW|CHE` 表示「法国全境 + 巴伐利亚 + 巴登-符腾堡 + 整个瑞士」。

## 邻邦清单（neighbor_adm0）

| ISO3 | 区域 | 历史相关性 |
|---|---|---|
| TUR | 安纳托利亚 | 拜占庭、奥斯曼帝国、十字军路径 |
| SYR | 叙利亚 | 罗马、拜占庭、十字军、奥斯曼 |
| LBN | 黎巴嫩 | 腓尼基（推罗、西顿）、十字军 |
| ISR | 以色列 / 巴勒斯坦 | 圣地、十字军、罗马犹太行省 |
| JOR | 约旦 | 十字军、奥斯曼 |
| EGY | 埃及 | 托勒密、罗马、拜占庭、法蒂玛、马穆鲁克、奥斯曼 |
| LBY | 利比亚 | 罗马阿非利加行省、汪达尔、阿拉伯、奥斯曼 |
| TUN | 突尼斯 | 迦太基、罗马、汪达尔、阿拉伯、奥斯曼 |
| DZA | 阿尔及利亚 | 努米底亚、罗马、汪达尔、阿拉伯、奥斯曼 |
| MAR | 摩洛哥 | 毛里塔尼亚、罗马、阿拉伯、马里尼德 |
| IRN | 伊朗 | 安息、萨珊、阿巴斯（与拜占庭东境长期对抗） |
| IRQ | 伊拉克 | 萨珊、阿拉伯哈里发、奥斯曼（与十字军、拜占庭交错） |

## 法律

geoBoundaries 数据采用 Open Data Commons Open Database License 1.0（ODbL）。详见 `ODbL-1.0-NOTICE.md`（由 prepare 脚本生成）。
