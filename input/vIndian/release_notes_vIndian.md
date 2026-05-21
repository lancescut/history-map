# 古印度政权数据 (vIndian) Release Notes

本文档记录了对 `vIndian` 目录下的古印度政权主表和年度表进行的人工交叉验证、去神话化及信史校准记录。

## 版本记录

### 版本号: v1.0.0-batch1 (古印度史前与信史年代学校对)
*   **发布日期**: 2026-05-19 17:26
*   **修改文件**: `indian_history_polities_master_vIndian.csv`, `indian_history_polities_yearly_vIndian.csv`
*   **更新影响行数**: 删除了 Yearly 表中 **2,240 行** 属于神话时期的无效年度数据。
*   **更新影响政权数**: 8 个核心政权

**详细更新内容**:

1.  **剔除“神话起源”，回归信史**
    *   **Tripura (特里普拉土邦, `polity_ind_0263`)**:
        *   **修正前**：100 年 - 1947 年
        *   **修正后**：**1400 年** - 1947 年
        *   **说明**：公元 100 年建国说源于《Rajmala》中对“月亮王朝”的神话追溯。真实可考的信史特里普拉王国 (Twipra Kingdom) 是在约公元 1400 年 (Maha Manikya 统治时期) 才成型。系统已删除了前 1300 年的无效神话年度行。
    *   **Udaipur (乌代浦/梅瓦尔, `polity_ind_0264`)**:
        *   **修正前**：530 年 - 1947 年
        *   **修正后**：**728 年** - 1947 年
        *   **说明**：530 年为古希拉王朝传说的起源，学界公认梅瓦尔王国的真正奠基人是巴帕·拉瓦尔 (Bappa Rawal)，他于公元 728 年占领吉多尔。
    *   **Chamba (羌巴, `polity_ind_0111`)**:
        *   **修正说明**：保留了其 500 年的建国传说，但强制追加了 `approx_or_uncertain` 的风险标记，并在史料来源中明确批注该年代缺乏严密文字考证。

2.  **纠正备受争议的“长年代学”**
    *   **百乘王朝 (Satavahana, `polity_ind_0027`)**:
        *   **修正前**：公元前 230 年 - 公元 220 年
        *   **修正后**：**公元前 100 年** - 公元 220 年
        *   **说明**：前 230 年是基于《往世书》的推断。结合阿育王铭文及现代考古学（Richard Salomon 等主张），其作为独立帝国的崛起应在前 1 世纪。

3.  **十六大国 (Mahajanapadas) 兼并史精细化**
    *   修正了之前大量列国被粗暴统一在“公元前 300 年”结束的错误，根据真实的吞并时间重置了灭亡节点：
    *   **鸯伽 (Anga)**：修正为约 **前 530 年** 被摩揭陀频毗娑罗吞并。
    *   **迦尸 (Kasi)**：修正为约 **前 490 年** 被拘萨罗和摩揭陀瓜分。
    *   **拘萨罗 (Kosala)**：修正为约 **前 460 年** 被摩揭陀阿阇世吞并。
    *   **阿槃提 (Avanti)**：修正为约 **前 400 年** 被摩揭陀希舒那伽王朝消灭。

---

### 版本号: v1.0.1-mythology-layer (神话/史诗资料分层)
*   **发布日期**: 2026-05-19
*   **修改文件**: `mythological_timeline_vIndian.csv`, `dataset_manifest_vIndian.json`, `indian_history_sources_vIndian.csv`, `indian_history_unresolved_or_disputed_vIndian.csv`, `mythology_research_notes_vIndian.md`
*   **更新影响**: 新增 12 条神话、史诗、往世书年代和王朝祖源传统记录；不改变历史政权年度表。

**详细更新内容**:

1.  新增 `mythological_timeline_vIndian.csv`，把《摩诃婆罗多》《罗摩衍那》《往世书》谱系、《Rajmala》早期特里普拉王表、梅瓦尔 Guhila/Bappa Rawal 祖源传统、Chamba 建国传说、百乘王朝前 230 年往世书长年代等资料从史实表中分离出来。
2.  新增字段 `historicity_status` 和 `historical_boundary_note`，明确每条资料是 `epic_tradition`、`puranic_chronology`、`legendary_dynastic_origin`、`textual_cultural_horizon` 还是 `mixed_history_memory`。
3.  将 `issue_ind_0002` 改为指向独立神话时间线：史诗和往世书传统可以播放和研究，但不能直接生成 polity yearly 行或实际控制地图。
4.  新增 `mythology_research_notes_vIndian.md`，记录本轮互联网可靠来源复核结论。
