# vIndian 神话、史诗与传说资料分层研究笔记

本轮核验结论：用户在 `release_notes_vIndian.md` 中把神话性年代从历史政权年表剥离出来的方向是正确的。新的 `mythological_timeline_vIndian.csv` 用于保存这些仍然重要的传统材料，但它们不再驱动 `polities_yearly`。

## 分层规则

- 历史史实层：进入 polity、ruler、event、capital 和 yearly 表；需要尽量有铭文、钱币、法律、官方档案、学术地图集或多源交叉支撑。
- 历史典故层：进入 anecdotes；可以是有历史人物或地点背景的故事，但不承担疆域和政权控制事实。
- 神话/史诗/王朝传说层：进入 mythological timeline；可按时间线播放，但 `historicity_status` 必须明确其为 `epic_tradition`、`puranic_chronology`、`legendary_dynastic_origin`、`textual_cultural_horizon` 或 `mixed_history_memory`。

## 本轮核验要点

- Tripura：Banglapedia 的 Rajmala 条目说明《Rajmala》在 1431 年宫廷整理，且前 135 位君主缺少考古或历史来源。因此公元 100 年式的远古王表只能入神话/王统传统层；polity 起年保留约 1400 更稳妥。
- Satavahana：Britannica 明确提到，依据往世书可把百乘王朝上溯，但百乘势力兴起更可放在前 1 世纪晚期，且早期统治者见于铭文。这支持从 `-230` 调整到 `-100`，并把 `-230` 保存为往世书年代传统。
- Chamba：Himachal Pradesh Chamba District 官方页面一方面说当地保存约 500 年以来的记录，另一方面把 Maru 称为 legendary hero，并称 Kalpagrama 为 mythical place。因此保留 500 年但标 `approx_or_uncertain` 是合适的。
- Mewar/Udaipur：Britannica 只支持 Guhilla/Mewar 的早期政治核心和 940 年独立；Treccani 采用 734 年 Bappa Rawal 建国说。现有 `728` 可作为传统近似起点，但应保留 `approx` 和传说说明；`530` 更适合移入神话/祖源传统层。
- Mahajanapadas：Britannica 的 Magadhan ascendancy 和 Kosala 条目支持 Magadha 吞并 Anga、Kashi、Kosala 的大方向；具体年份仍应作为 approximate。Anga/Kashi/Kosala/Avanti 的修正不属于神话，而属于早期史年代近似化。

## 使用方式

前端如要播放神话时间线，应只读取 `mythological_timeline_vIndian.csv` 或其未来生成产物，并用独立图层、独立颜色和独立说明文案展示。不得把这些节点合并进历史政权的实际控制区、统治者年表或史实事件默认图层。
