# 1912-1949 民国时期 v03 数据扩展研究方案

## 目标与范围

本方案用于扩展 v03 数据集，使系统能够覆盖 1912 年至 1949 年的中华民国大陆时期。扩展重点不是只补一条“中华民国”记录，而是用 v03 现有格式表达三类事实：第一，中央政权与地方割据、国共两党控制区的变化；第二，外国租借地、租界、割让地、战争占领区和傀儡政权造成的实际疆域变化；第三，外蒙古、西藏、新疆、东北、台湾等边疆或争议区域在法理主权与实际控制之间的差异。

本方案只设计数据与实现路径，不直接改动 v03 数据。下一步实施时，应保持 `input/v03/*.csv`、`scripts/build_historical_events_v03.py` 和 `scripts/generate_public_data.py` 的现有约束，避免破坏公开 JSON 的兼容性。

## 已确认的本地 v03 格式约束

当前公开数据的 `year_max` 是 1912，`public/data/v03/years/1913.json` 与 `1949.json` 不存在；`scripts/build_historical_events_v03.py` 和 `scripts/generate_public_data.py` 都硬编码 `YEAR_MAX = 1912`。因此扩展民国段必须同时修改年度范围、政权事实源、年度展开、事件生成和公开数据生成。

政权主表格式位于 `input/v03/chinese_history_polities_master_v03.csv`，关键字段包括 `polity_id`、`macro_period`、`dynasty_name`、`polity_name`、`polity_aliases`、`polity_display_name`、`polity_type`、起止年、历史地理、现代行政区近似、都城、创建者/末任、来源、置信度和争议说明。年度表 `input/v03/chinese_history_polities_yearly_v03.csv` 是展开结果，不应作为唯一事实源手工维护。

事件表 `input/v03/historical_events_v03.csv` 的字段由 `scripts/build_historical_events_v03.py` 的 `FIELDNAMES` 控制，包括 `event_id`、`year`、`sort_order`、`coverage_role`、`event_type`、`title`、`description`、`related_polity_ids`、地点、来源、置信度与审核状态。新增事件应优先进入脚本的 `SUPPLEMENTAL_EVENT_SPECS`、`RANGE_ANCHOR_SPECS` 与 `LOCATION_GAZETTEER`，避免直接编辑生成后的 CSV 被覆盖。

当前 `territory_overrides_v03.csv` 虽有 `valid_from_year` 和 `valid_to_year`，但 `generate_public_data.py` 目前按 `polity_id -> override` 读取，不能同一个 `polity_id` 多时段切换疆域。为保持兼容，本轮建议用“阶段性 polity”表达剧烈变化的控制区；如果后续要更精确，应单独改造 territory loader 为按年份选择 override。

## 历史事实分层原则

民国时期不能把“主权宣称”和“实际控制”混为一层。数据中建议统一使用以下口径：

| 层级 | 数据表达 | 示例 |
|---|---|---|
| 法理/名义中央 | `polity_type=共和国/中央政权`，说明名义范围 | 中华民国北京政府、南京国民政府 |
| 实际控制区 | 阶段性 polity 或 range_anchor，低/中置信疆域近似 | 北洋军阀、国民政府控制区、中共根据地/解放区 |
| 外国租借/租界 | `polity_type=租借地/租界/殖民管治区`，与中国政权并列显示 | 关东州、威海卫、广州湾、上海公共租界 |
| 外国占领/傀儡政权 | `polity_type=占领区/傀儡政权`，来源明确标注 | 满洲国、汪伪政权、日占香港 |
| 争议/事实自治 | `issue_type=effective_control_dispute` 或 `chronology_variant` | 外蒙古、西藏、新疆三区 |

## 建议新增政权/控制区记录

为兼容现有静态疆域近似，建议不要只建一个 1912-1949 的“中华民国”。更稳妥的方式是按政治阶段拆为若干 `polity_id`，并用 `polity_aliases` 和 `polity_name_disambiguation` 说明它们同属中华民国历史阶段。

| 建议 ID | 名称 | 年份 | 类型 | 用途 |
|---|---:|---:|---|---|
| `polity_0183` | 中华民国临时政府/北京政府 | 1912-1928 | 共和国/中央政权 | 表达北洋政府名义中央及军阀割据背景 |
| `polity_0184` | 广州/武汉国民政府 | 1917-1928 | 革命政府/对立中央 | 表达护法、国民革命与北伐时期南方政权 |
| `polity_0185` | 中华民国国民政府 | 1925-1949 | 共和国/中央政权 | 表达南京、重庆、战后南京及 1949 迁台 |
| `polity_0186` | 中华苏维埃共和国 | 1931-1937 | 革命根据地政权 | 表达中央苏区与瑞金政权 |
| `polity_0187` | 陕甘宁边区及中共抗日根据地 | 1937-1945 | 边区/根据地 | 表达第二次国共合作下的中共控制区 |
| `polity_0188` | 中国共产党解放区 | 1945-1949 | 根据地/军事控制区 | 表达内战后期控制区扩张 |
| `polity_0189` | 满洲国 | 1932-1945 | 傀儡政权 | 表达日本扶植的东北政权 |
| `polity_0190` | 汪精卫南京国民政府 | 1940-1945 | 傀儡政权 | 表达日本占领区名义政权 |
| `polity_0191` | 蒙疆联合自治政府 | 1939-1945 | 傀儡政权/占领区 | 表达日占内蒙古西部政治安排 |
| `polity_0192` | 日本台湾总督府 | 1895-1945 | 殖民管治区 | 表达台湾、澎湖在 1912-1945 的日本统治及 1945 接收 |
| `polity_0193` | 日本关东州租借地 | 1905-1945 | 租借地/殖民管治区 | 表达旅顺、大连及南满权益核心 |
| `polity_0194` | 英属威海卫 | 1898-1930 | 租借地 | 表达 1930 年归还中华民国 |
| `polity_0195` | 法属广州湾 | 1898-1945 | 租借地 | 表达抗战后归还并改湛江 |
| `polity_0196` | 英属香港 | 1842-1941; 1945-1949 | 殖民管治区 | 可拆两条或以事件说明 1941-1945 日占 |
| `polity_0197` | 日占香港 | 1941-1945 | 战争占领区 | 表达香港被日本军事占领 |
| `polity_0198` | 葡属澳门 | 1887-1949 | 殖民管治区 | 表达葡萄牙实际行政，非 1945 收回 |
| `polity_0199` | 外蒙古/蒙古人民共和国 | 1911-1949 | 事实独立/邻国 | 表达 1911 独立、1915 自治、1924 建国、1945 公投、1946 承认 |
| `polity_0200` | 西藏噶厦政权 | 1912-1949 | 事实自治/争议地区 | 表达清末后事实自治，保留主权争议说明 |
| `polity_0201` | 新疆三区革命政权 | 1944-1949 | 地方政权/苏联影响区 | 表达伊犁、塔城、阿山三区实际控制 |

其中 `polity_0196` 英属香港有一个实现选择：若严格展示 1941-1945 日占断点，则拆成 `英属香港 1842-1941`、`日占香港 1941-1945`、`英属香港 1945-1949` 三个 polity；若保持条目数较少，则保留英属香港一条，并用 1941、1945 事件标注控制变化。为了地图年度准确性，建议拆分。

## 建议新增关键事件组

事件数量建议控制在首批 45-60 条，覆盖每个关键年份和每个疆域变化节点。事件类型应复用现有标签：`dynasty_start`、`dynasty_end`、`war`、`diplomacy`、`treaty`、`institution`、`event`、`capital_relocation`、`range_anchor`。如需更细，可以在 `event-meta.ts` 后续增补 `occupation`、`cession`、`retrocession`、`civil_war_control`，但首批可先用 `treaty/war/event` 保持兼容。

| 年份 | 建议事件 | 类型 | 重点 |
|---:|---|---|---|
| 1912 | 中华民国临时政府成立、清帝退位、北京政府形成 | dynasty_start/event | 民国开端与中央转移 |
| 1914 | 唐努乌梁海成为俄国保护地 | diplomacy | 边疆实际控制变化 |
| 1915 | 二十一条与中俄蒙恰克图协定 | treaty | 日本权益扩大、外蒙古自治 |
| 1916 | 护国战争结束、袁世凯死亡 | war/event | 北洋中央权威破裂 |
| 1917 | 护法运动、德国/奥匈在华权益取消 | event/treaty | 南北对立与租界变化 |
| 1919 | 巴黎和会山东问题、五四运动 | diplomacy/event | 青岛/山东权益争议 |
| 1921 | 中国共产党成立、蒙古革命 | event | 后续内战与外蒙古演变 |
| 1922 | 胶澳/青岛归还中国 | treaty | 德租胶澳经日本占领后回归 |
| 1924 | 国民党一大与第一次国共合作、蒙古人民共和国成立 | event | 国民革命与外蒙古事实国家化 |
| 1925 | 广州国民政府成立 | dynasty_start | 南方革命政府形成 |
| 1926 | 北伐开始 | war | 国民革命势力北上 |
| 1927 | 南京国民政府成立、清党、南昌起义、秋收起义 | event/war | 国共分裂与中共武装根据地起点 |
| 1928 | 东北易帜、国民政府名义统一全国 | event | 北洋结束、南京十年开始 |
| 1930 | 威海卫归还中国、中原大战 | treaty/war | 租借地回归与国内军事重组 |
| 1931 | 九一八事变、中华苏维埃共和国成立 | war/dynasty_start | 东北丧失与苏区政权形成 |
| 1932 | 满洲国成立、一二八淞沪抗战 | dynasty_start/war | 日本傀儡政权与上海战事 |
| 1933 | 塘沽协定、第一次东突厥斯坦共和国 | treaty/event | 华北缓冲与新疆变局 |
| 1934 | 中央红军长征开始 | war/event | 苏区控制区转移 |
| 1935 | 遵义会议、华北自治压力 | event | 中共领导层变化与日本华北推进 |
| 1936 | 西安事变 | event | 第二次国共合作前奏 |
| 1937 | 七七事变、淞沪会战、南京陷落、国民政府迁重庆 | war/capital_relocation | 全面抗战与实际控制断裂 |
| 1938 | 武汉、广州失守 | war | 国民政府控制重心转入西南 |
| 1940 | 汪精卫南京政权成立、百团大战 | dynasty_start/war | 占领区名义政权与中共敌后根据地 |
| 1941 | 香港被日本占领、皖南事变 | war/event | 外国殖民地被战争占领、国共摩擦 |
| 1943 | 中美中英新约、上海公共租界等治外法权终止、开罗宣言 | treaty/diplomacy | 租界制度法理终结、台湾归还承诺 |
| 1944 | 豫湘桂战役、唐努乌梁海并入苏联、三区革命 | war/event | 日本占领区最大扩展与边疆变化 |
| 1945 | 日本投降、台湾澎湖接收、苏军进东北、广州湾归还、外蒙古公投 | treaty/war/event | 战后疆域重大重组 |
| 1946 | 中华民国承认外蒙古独立、全面内战爆发 | diplomacy/war | 法理疆域收缩与内战重启 |
| 1947 | 国民政府攻占延安、刘邓大军挺进大别山、台湾二二八事件 | war/event | 内战攻守转换与台政危机 |
| 1948 | 辽沈、淮海、平津三大战役 | war | 东北、华东、华北控制权逆转 |
| 1949 | 渡江战役、南京/上海/广州/重庆/成都易手、中华人民共和国成立、中华民国政府迁台 | war/dynasty_start/capital_relocation | 大陆政权转换和海峡分治开端 |

## 范围锚点建议

为避免每一年没有事件时地图空白，应增加以下 `range_anchor`。这些锚点不表示某年突发事件，而表示该年处于某个历史进程中。

| anchor_id | 年份 | 标题 |
|---|---:|---|
| `republic_beiyang_warlord` | 1912-1927 | 民国初建与北洋军阀割据 |
| `national_revolution_northern_expedition` | 1924-1928 | 国民革命与北伐统一 |
| `nanjing_decade_fragmented_unity` | 1928-1937 | 南京十年与边疆危机 |
| `japanese_invasion_occupied_china` | 1931-1945 | 日本侵占东北、华北与沿海 |
| `war_of_resistance_dual_control` | 1937-1945 | 抗战时期国统区、敌占区与中共根据地并存 |
| `postwar_civil_war_control_shift` | 1945-1949 | 战后接收与国共内战控制区转移 |

## 资料与核验依据

已检索到的资料可支撑首批数据设计。后续实施时，每条 CSV 记录仍需在 `source_titles/source_urls/source_raw/confidence_note` 中保留最直接来源。

| 主题 | 可用来源 |
|---|---|
| 民国政权、北洋、国民政府、北伐、南京十年 | Britannica 的 Republic of China/China 条目、中华民国政府沿革资料、国史馆/中研院史事日志候选来源 |
| 国共内战 1945-1949 | Britannica Chinese Civil War、美国国务院 Office of the Historian、中国近现代史教材/年表 |
| 台湾与澎湖 | 1895 《马关条约》、1943 开罗宣言、1945 日本投降与接收资料 |
| 东北与满洲国 | Britannica Manchukuo、九一八事变/满洲国资料、1945 苏军进攻东北资料 |
| 外蒙古 | Britannica Mongolia、1915 恰克图协定、1945 公投、1946 中华民国承认 |
| 西藏 | Britannica Tibet、1914 西姆拉会议资料，需在争议表标注“事实自治/主权争议” |
| 租借地/租界 | 威海卫、广州湾、关东州、胶澳、上海公共租界、上海法租界、香港、澳门的条约与归还资料 |
| 第二次世界大战期间占领区 | 日本侵华战争、汪精卫政权、蒙疆、香港日占、豫湘桂战役资料 |

初步检索链接：

- Encyclopaedia Britannica, "Chinese Civil War": https://www.britannica.com/event/Chinese-Civil-War
- Encyclopaedia Britannica, "Manchukuo": https://www.britannica.com/place/Manchukuo
- Encyclopaedia Britannica, "Mongolia - Between Russia and China": https://www.britannica.com/place/Mongolia/Between-Russia-and-China
- Office of the Historian, "The Chinese Revolution of 1949": https://history.state.gov/milestones/1945-1952/chinese-rev
- Yale Avalon Project, "Cairo Conference 1943": https://avalon.law.yale.edu/wwii/cairo.asp
- Yale Avalon Project, "Potsdam Declaration": https://avalon.law.yale.edu/20th_century/decade17.asp
- British Weihaiwei overview: https://en.wikipedia.org/wiki/British_Weihaiwei
- Guangzhouwan overview: https://en.wikipedia.org/wiki/Guangzhouwan
- Kiautschou Bay / Jiaozhou Bay Leased Territory overview: https://en.wikipedia.org/wiki/Kiautschou_Bay_Leased_Territory
- Kwantung Leased Territory overview: https://en.wikipedia.org/wiki/Kwantung_Leased_Territory
- Shanghai International Settlement overview: https://en.wikipedia.org/wiki/Shanghai_International_Settlement
- Shanghai French Concession overview: https://en.wikipedia.org/wiki/Shanghai_French_Concession
- Hong Kong Japanese occupation overview: https://en.wikipedia.org/wiki/Japanese_occupation_of_Hong_Kong
- Macau history overview: https://en.wikipedia.org/wiki/History_of_Macau
- Republic of China government evolution overview: https://zh.wikipedia.org/wiki/%E4%B8%AD%E5%8D%8E%E6%B0%91%E5%9B%BD%E6%94%BF%E5%BA%9C%E6%B2%BF%E9%9D%A9

维基类来源只应作为线索和字段初稿来源；最终事实应优先用条约文本、政府档案、权威百科、年表、教材和学术来源复核。

## 实施方案

第一步，新增一个幂等脚本 `scripts/add_republican_period_v03.py`，仿照 `scripts/add_missing_polities_v03.py`。脚本直接维护民国段新增 polity、rulers、capital events、issues，并自动展开 yearly rows。这样不会污染 `generate_v03_from_v02.py` 的 v02 拆表逻辑，也方便重复运行。

第二步，修改 `package.json` 的 `generate:data`，在事件和公开数据生成前运行新增脚本。建议顺序是：`audit_polity_names_v03.py`、`add_republican_period_v03.py`、`build_historical_events_v03.py`、边界准备、`generate_public_data.py`。如果担心脚本重入顺序，可以让 `add_republican_period_v03.py` 每次先剔除 `polity_0183` 以后白名单记录再追加。

第三步，将 `scripts/build_historical_events_v03.py` 的 `YEAR_MAX` 改为 1949，新增民国地点词典：南京、北京、广州、武汉、重庆、瑞金、延安、沈阳、长春、哈尔滨、台北、基隆、青岛、威海、湛江、上海、天津、旅顺/大连、乌兰巴托、拉萨、伊宁、香港、澳门等。

第四步，在事件脚本中新增 `ROC_SOURCES`、`CIVIL_WAR_SOURCES`、`TREATY_SOURCES` 等 source pair，并加入上表的 `SUPPLEMENTAL_EVENT_SPECS` 与 `RANGE_ANCHOR_SPECS`。新增事件先使用 `event_type` 现有值；如果 UI 需要更清晰，再在 `src/event-meta.ts` 追加 `occupation`、`cession`、`retrocession` 标签。

第五步，将 `scripts/generate_public_data.py` 的 `YEAR_MAX` 改为 1949，并检查 metadata、years 文件、events、contexts 是否覆盖 1913-1949。若采用阶段性 polity，不需要改 territory loader；若采用单一中华民国 polity + 年度疆域，则必须先重构 territory override 为按年份选择。

第六步，运行校验：`python3 scripts/validate_v03.py`、`npm run generate:data`、`npm run build`。重点检查 `year_sort_order`、`polity_year_completeness`、`yearly_polity_id_join`、`historical_event_years` 是否覆盖到 1949。

## 风险与处理

最大风险是“地图疆域过度精确”。v03 当前用现代行政边界近似拼合，民国内战时期控制线按县级精准到年份并不现实。首批应以省级/区域近似为主，`confidence_score` 对动态战线保持 45-70，`confidence_note` 明确“阶段性势力范围近似，非逐日战线”。

第二个风险是政治敏感与史实口径。外蒙古、西藏、台湾、租界、满洲国、汪伪政权都必须把“法理主权/承认情况/实际控制/傀儡性质”写入 `polity_name_disambiguation`、`confidence_note` 或 unresolved issue，不用单一颜色暗示一种未说明的结论。

第三个风险是事件过多导致时间轴噪声。首批建议只放核心 45-60 条，其他地方战役用 range_anchor 或后续故事预设承载。若后续做专题故事线，可再加“租界收回”“东北沦陷与收复”“国共内战三大战役”“边疆争议与事实控制”等 story presets。
