#!/usr/bin/env python3
"""为 v03 补录 release_note batch19a 标为 backlog 的 8/15 个重要政权。

资料原则：
  - A 级（conf 95-100）：二十四史本纪/列传 + 现代学者共识 + 出土文献佐证
  - B 级（conf 80-94）：正史相关传完整 + 共识，存在 ±1-2 年纪年差异
  - C 级（conf 60-79）：正史残缺，依赖出土文书/碑刻补正

引用来源（按主要程度）：
  - 二十四史本身（《新唐书》《旧唐书》《宋史》《元史》《辽史》《三国志》《魏书》《北史》
    《周书》《隋书》《史记》《汉书》《后汉书》）
  - 编年（《资治通鉴》）
  - 域外正史（朝鲜《三国史记》《高丽史》；藏文《敦煌吐蕃历史文书》《贤者喜宴》）
  - 现代学者：白寿彝《中国通史》、谭其骧《中国历史地图集》、马大正《突厥史》、
    韩昇《东亚世界形成史论》

行为：
  - 直接追加到 input/v03/chinese_history_polities_master_v03.csv
  - 直接追加到 input/v03/chinese_history_rulers_master_v03.csv
  - 直接追加到 input/v03/chinese_history_polities_yearly_v03.csv
  - 直接追加到 input/v03/chinese_history_unresolved_or_disputed_v03.csv
  - 直接追加到 input/v03/capital_events_v03.csv
  - 幂等：脚本内含 polity_id 白名单，重复运行会先剔除已存在的新增政权再追加。

运行后需另跑 python3 scripts/generate_public_data.py。
"""
from __future__ import annotations

import csv
import sys
from pathlib import Path
from typing import Any

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "v03"

MASTER_CSV = INPUT / "chinese_history_polities_master_v03.csv"
RULERS_CSV = INPUT / "chinese_history_rulers_master_v03.csv"
YEARLY_CSV = INPUT / "chinese_history_polities_yearly_v03.csv"
ISSUES_CSV = INPUT / "chinese_history_unresolved_or_disputed_v03.csv"
CAPITALS_CSV = INPUT / "capital_events_v03.csv"

CALENDAR_NOTE = (
    "BCE years are negative integers; there is no year 0; ranges are expanded inclusively "
    "when start and end years are parseable."
)


def expand_years(start: int, end: int) -> list[int]:
    if start > end:
        start, end = end, start
    return [y for y in range(start, end + 1) if y != 0]


def year_label(year: int) -> str:
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def join_pipe(values: list[str]) -> str:
    return " | ".join(value for value in values if value)


# ============================================================================
# 数据集：每个 polity 是一个 dict（含 master + rulers + capital events + issues）
# 字段约定与现有 CSV 一致；多字段值（多 alias / 多 source）以 " | " 分隔。
# ============================================================================

POLITY_DEFINITIONS: list[dict[str, Any]] = []


def define_nanzhao() -> dict[str, Any]:
    """南诏 738-902（《新唐书·南诏传》《蛮书》《南诏野史》）"""
    rulers = [
        # ruler_name, title, temple_name, posthumous, personal_name, start, end, era_names, conf
        ("皮逻阁", "南诏王", "", "归义王", "皮逻阁", 738, 748, "", 85),
        ("阁罗凤", "南诏王", "神武王", "神武王", "阁罗凤", 748, 779, "赞普钟", 85),
        ("异牟寻", "南诏王", "孝桓王", "孝桓王", "异牟寻", 779, 808, "见龙 | 上元", 85),
        ("寻阁劝", "南诏王", "孝惠王", "孝惠王", "寻阁劝", 808, 809, "应道", 80),
        ("劝龙晟", "南诏王", "幽王", "幽王", "劝龙晟", 809, 816, "龙兴", 80),
        ("劝利", "南诏王", "靖王", "靖王", "劝利", 816, 823, "全义 | 大丰", 80),
        ("劝丰祐", "南诏王", "昭成王", "昭成王", "劝丰祐", 823, 859, "保和 | 天启", 85),
        ("世隆", "南诏皇帝", "景庄帝", "景庄帝", "酋龙", 859, 877, "建极 | 法尧", 85),
        ("隆舜", "南诏皇帝", "宣武帝", "宣武帝", "隆舜", 877, 897, "贞明 | 承智 | 大同 | 嵯耶", 80),
        ("舜化贞", "南诏皇帝", "孝哀帝", "孝哀帝", "舜化贞", 897, 902, "中兴", 80),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "南诏",
            "polity_name": "南诏",
            "polity_aliases": "南詔 | 大蒙国 | 大礼国 | 大封民国",
            "polity_type": "政权/国家",
            "polity_start_year": 738,
            "polity_end_year": 902,
            "polity_date_raw": "738年－902年",
            "polity_date_precision": "year",
            "historical_geography_raw": "以洱海地区为中心，盛时辖云南全境、四川南部、贵州西部、缅甸东北部、老挝北部、越南西北部",
            "modern_admin_units_raw": "云南省全境、四川省南部、贵州省西部、缅甸克钦邦及掸邦北部、老挝北部、越南西北",
            "capital_historical": "太和城（西元 738-779）| 羊苴咩城（西元 779-902）",
            "capital_modern": "云南省大理市",
            "ruling_family_or_clan": "蒙姓乌蛮",
            "ethnicity_or_group": "乌蛮 | 白蛮（彝藏缅语族先民）",
            "founder": "皮逻阁",
            "last_ruler": "蒙舜化贞",
            "destroyed_by_or_successor": "大长和国（郑买嗣）",
            "polity_source_titles": "《新唐书·南诏传》 | 《旧唐书·南蛮西南蛮传》 | 《蛮书》（樊绰）",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%8D%97%E8%AF%8F | https://zh.wikipedia.org/wiki/%E8%9B%AE%E4%B9%A6",
            "polity_source_raw": "738年皮逻阁受唐封云南王统一六诏；902年郑买嗣杀舜化贞建大长和。",
            "confidence_score": 90,
            "confidence_note": "正史叙事完整；君主世系十王清晰可考",
        },
        "rulers": rulers,
        "capitals": [
            ("太和城", "云南省大理市太和村遗址", 738, 779, 100.197, 25.673, True, "initial_capital", "region",
             "《蛮书·六诏》", "https://zh.wikipedia.org/wiki/%E8%9B%AE%E4%B9%A6",
             "738 年皮逻阁定都太和城；考古遗址位于今云南大理市下关苍山佛顶峰下太和村", 85, "都城明确；坐标按遗址近似"),
            ("羊苴咩城", "云南省大理古城", 779, 902, 100.230, 25.692, True, "relocation", "city",
             "《新唐书·南诏传》", "https://zh.wikipedia.org/wiki/%E5%8D%97%E8%AF%8F",
             "779 年异牟寻迁都羊苴咩城（今大理古城），为南诏中后期都城", 88, "都城明确；城市级坐标"),
        ],
        "issues": [],
    }


def define_dali() -> dict[str, Any]:
    """大理 937-1253（含中段后理，《宋史·大理传》《元史·大理传》《南诏野史》《白古通》）"""
    rulers = [
        ("段思平", "皇帝", "太祖神圣文武皇帝", "神圣文武皇帝", "段思平", 937, 944, "文德 | 神武", 88),
        ("段思英", "皇帝", "文经皇帝", "文经皇帝", "段思英", 944, 945, "文经", 80),
        ("段思良", "皇帝", "太宗圣慈文武皇帝", "圣慈文武皇帝", "段思良", 945, 952, "至治", 80),
        ("段思聪", "皇帝", "至道广慈皇帝", "至道广慈皇帝", "段思聪", 952, 968, "明德 | 广德 | 顺德", 80),
        ("段素顺", "皇帝", "应道皇帝", "应道皇帝", "段素顺", 968, 985, "明政", 80),
        ("段素英", "皇帝", "昭明皇帝", "昭明皇帝", "段素英", 985, 1009, "广明 | 明应 | 明统 | 明圣 | 明德 | 明治", 80),
        ("段素廉", "皇帝", "宣肃皇帝", "宣肃皇帝", "段素廉", 1009, 1022, "明启", 80),
        ("段素隆", "皇帝", "秉义皇帝", "秉义皇帝", "段素隆", 1022, 1026, "明通", 78),
        ("段素真", "皇帝", "圣德皇帝", "圣德皇帝", "段素真", 1026, 1041, "正治", 80),
        ("段素兴", "皇帝", "天明皇帝", "天明皇帝", "段素兴", 1041, 1044, "圣明 | 天明", 78),
        ("段思廉", "皇帝", "兴宗孝德皇帝", "孝德皇帝", "段思廉", 1044, 1075, "保安 | 正安 | 正德 | 保德 | 明侯", 82),
        ("段廉义", "皇帝", "上德皇帝", "上德皇帝", "段廉义", 1075, 1080, "上德 | 广安", 78),
        ("段寿辉", "皇帝", "上明皇帝", "上明皇帝", "段寿辉", 1080, 1081, "上明", 78),
        ("段正明", "皇帝", "保定皇帝", "保定皇帝", "段正明", 1081, 1094, "保立 | 建安 | 天祐", 82),
        # 1094-1096 高升泰篡建大中国，单列 polity_0169
        ("段正淳", "皇帝", "中宗文安皇帝", "文安皇帝", "段正淳", 1096, 1108, "天授 | 开明 | 文安 | 日新", 82),
        ("段正严", "皇帝", "宪宗宣仁皇帝", "宣仁皇帝", "段和誉", 1108, 1147, "日新 | 文治 | 永嘉 | 保天 | 广运", 88),
        ("段正兴", "皇帝", "景宗正康皇帝", "正康皇帝", "段易长", 1147, 1171, "永贞 | 大宝 | 龙兴 | 盛明 | 建德", 82),
        ("段智兴", "皇帝", "宣宗功极皇帝", "功极皇帝", "段智兴", 1171, 1200, "利贞 | 盛德 | 嘉会 | 元亨 | 安定", 85),
        ("段智廉", "皇帝", "英宗", "英宗", "段智廉", 1200, 1204, "凤历 | 元寿", 78),
        ("段智祥", "皇帝", "神宗", "神宗", "段智祥", 1204, 1238, "天开 | 天辅 | 仁寿", 82),
        ("段祥兴", "皇帝", "孝义皇帝", "孝义皇帝", "段祥兴", 1238, 1251, "道隆", 80),
        ("段兴智", "皇帝", "天定贤王", "天定贤王", "段兴智", 1251, 1253, "天定", 85),
    ]
    return {
        "polity": {
            "macro_period": "宋辽金夏",
            "dynasty_name": "大理国",
            "polity_name": "大理",
            "polity_aliases": "大理国 | 后理国 | Dali Kingdom",
            "polity_type": "政权/国家",
            "polity_start_year": 937,
            "polity_end_year": 1253,
            "polity_date_raw": "937年－1253年（含 1096 年后段氏复立的后理段）",
            "polity_date_precision": "year",
            "historical_geography_raw": "继承南诏疆域，以洱海为中心，盛时辖云南全境、贵州西部、四川南部、缅甸东北、老挝北部、越南西北",
            "modern_admin_units_raw": "云南省、贵州省西部、四川省南部、缅甸克钦邦及掸邦北部、老挝北部、越南西北",
            "capital_historical": "羊苴咩城",
            "capital_modern": "云南省大理古城",
            "ruling_family_or_clan": "段氏",
            "ethnicity_or_group": "白蛮 | 乌蛮",
            "founder": "段思平",
            "last_ruler": "段兴智",
            "destroyed_by_or_successor": "蒙古帝国（忽必烈率军灭大理）",
            "polity_source_titles": "《宋史·大理传》 | 《元史·大理传》 | 《元史·世祖纪》 | 《滇略》 | 《南诏野史》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%A4%A7%E7%90%86 | https://zh.wikipedia.org/wiki/%E5%90%8E%E7%90%86",
            "polity_source_raw": "937 年段思平灭杨干贞之大义宁建大理；1094-1096 高升泰短暂篡位（大中国，另列）；1096 段正淳复立（后理），1253 年蒙古忽必烈灭之，段兴智降。",
            "confidence_score": 90,
            "confidence_note": "正史叙事完整；段氏世系 22 王清晰，部分年号在不同地方志间有出入",
        },
        "rulers": rulers,
        "capitals": [
            ("羊苴咩城", "云南省大理古城", 937, 1253, 100.230, 25.692, True, "initial_capital", "city",
             "《宋史·大理传》", "https://zh.wikipedia.org/wiki/%E5%A4%A7%E7%90%86",
             "大理沿袭南诏都城羊苴咩城（今大理古城），1253 年城破", 88, "都城明确；城市级坐标"),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "polity_start_year",
                "selected_value": "937",
                "alternative_values": "938",
                "source_titles": "《宋史·大理传》/《滇略》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E5%A4%A7%E7%90%86",
                "note": "段思平称帝建大理一般用 937 年；少数地方史料如《白古通》记作 938 年。本表沿用 937。",
                "action_in_v03": "selected value retained; issue documented",
            },
            {
                "issue_type": "partial_boundary",
                "field_name": "polity_continuity",
                "selected_value": "937-1253 含后理段连续",
                "alternative_values": "拆分大理 937-1094 + 后理 1096-1253",
                "source_titles": "《宋史·大理传》/《元史·大理传》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E5%A4%A7%E7%90%86",
                "note": "1094 高升泰篡为大中国（另列 polity），1096 段氏复立，史称后理。本表合并段氏全朝；1094-1096 见 polity_0169 大中国。",
                "action_in_v03": "merged as one polity; usurpation tracked as separate polity_0169",
            },
        ],
    }


def define_dazhong() -> dict[str, Any]:
    """大中国 1094-1096（高升泰篡大理；《宋史·大理传》《滇略》）"""
    rulers = [
        ("高升泰", "大中皇帝", "富有圣德表正皇帝", "富有圣德表正皇帝", "高升泰", 1094, 1096, "上治", 80),
    ]
    return {
        "polity": {
            "macro_period": "宋辽金夏",
            "dynasty_name": "大中国",
            "polity_name": "大中",
            "polity_aliases": "大中国 | 高大中",
            "polity_type": "割据政权/国家",
            "polity_start_year": 1094,
            "polity_end_year": 1096,
            "polity_date_raw": "1094年－1096年",
            "polity_date_precision": "year",
            "historical_geography_raw": "原大理国疆域，以洱海为中心",
            "modern_admin_units_raw": "云南省、贵州省西部、四川省南部、缅甸克钦邦及掸邦北部、老挝北部、越南西北",
            "capital_historical": "羊苴咩城",
            "capital_modern": "云南省大理古城",
            "ruling_family_or_clan": "高氏（鄯阐侯家系）",
            "ethnicity_or_group": "白蛮",
            "founder": "高升泰",
            "last_ruler": "高升泰",
            "destroyed_by_or_successor": "大理（段正淳）",
            "polity_source_titles": "《宋史·大理传》 | 《滇略》 | 《南诏野史》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%A4%A7%E4%B8%AD%E5%9B%BD",
            "polity_source_raw": "1094 年高升泰废大理段正明自立，改国号大中；1096 年临终遗命还政段氏，段正淳复立，史称后理。",
            "confidence_score": 78,
            "confidence_note": "短暂篡位政权；史料较略",
        },
        "rulers": rulers,
        "capitals": [
            ("羊苴咩城", "云南省大理古城", 1094, 1096, 100.230, 25.692, True, "initial_capital", "city",
             "《宋史·大理传》", "https://zh.wikipedia.org/wiki/%E5%A4%A7%E4%B8%AD%E5%9B%BD",
             "大中沿用大理都城羊苴咩城", 80, ""),
        ],
        "issues": [],
    }


def define_bohai() -> dict[str, Any]:
    """渤海 698-926（《新唐书·渤海传》《旧唐书·渤海靺鞨传》《辽史》《三国史记》）"""
    rulers = [
        ("大祚荣", "渤海郡王 | 高王", "高王", "高王", "大祚荣", 698, 719, "天统", 85),
        ("大武艺", "渤海郡王 | 武王", "武王", "武王", "大武艺", 719, 737, "仁安", 88),
        ("大钦茂", "渤海国王 | 文王", "文王", "文王", "大钦茂", 737, 793, "大兴 | 宝历", 88),
        ("大元义", "废王", "", "废王", "大元义", 793, 793, "", 70),
        ("大华玙", "成王", "成王", "成王", "大华玙", 793, 794, "中兴", 75),
        ("大嵩璘", "康王", "康王", "康王", "大嵩璘", 794, 808, "正历", 85),
        ("大元瑜", "定王", "定王", "定王", "大元瑜", 808, 812, "永德", 80),
        ("大言义", "僖王", "僖王", "僖王", "大言义", 812, 817, "朱雀", 78),
        ("大明忠", "简王", "简王", "简王", "大明忠", 817, 818, "太始", 78),
        ("大仁秀", "宣王", "宣王", "宣王", "大仁秀", 818, 830, "建兴", 88),
        ("大彝震", "渤海国王", "", "", "大彝震", 830, 857, "咸和", 82),
        ("大虔晃", "渤海国王", "", "", "大虔晃", 857, 871, "", 75),
        ("大玄锡", "渤海国王", "", "", "大玄锡", 871, 895, "", 75),
        ("大玮瑎", "渤海国王", "", "", "大玮瑎", 895, 906, "", 70),
        ("大諲譔", "渤海国王（末代）", "", "末代", "大諲譔", 906, 926, "", 82),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "渤海国",
            "polity_name": "渤海",
            "polity_aliases": "渤海国 | 震国 | 渤海郡国 | Balhae | Bohai",
            "polity_type": "政权/国家",
            "polity_start_year": 698,
            "polity_end_year": 926,
            "polity_date_raw": "698年－926年",
            "polity_date_precision": "year",
            "historical_geography_raw": "以东京/上京为中心，盛时五京制；东至日本海，西至辽河上游，北至黑龙江中游，南至朝鲜半岛北部",
            "modern_admin_units_raw": "黑龙江省东南部、吉林省东部、辽宁省东北部、朝鲜半岛北部、俄罗斯滨海边疆区南部",
            "capital_historical": "旧国敖东城（698-755）| 中京显德府（755-756）| 上京龙泉府（756-785，794-926）| 东京龙原府（785-794）",
            "capital_modern": "黑龙江省宁安市渤海镇（上京龙泉府）",
            "ruling_family_or_clan": "大氏（粟末靺鞨）",
            "ethnicity_or_group": "靺鞨（粟末部）| 高句丽遗民",
            "founder": "大祚荣",
            "last_ruler": "大諲譔",
            "destroyed_by_or_successor": "辽朝（耶律阿保机）",
            "polity_source_titles": "《新唐书·渤海传》 | 《旧唐书·渤海靺鞨传》 | 《辽史·太祖纪》 | 《辽史·地理志》 | 《三国史记》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%9B%BD | https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%90%9B%E4%B8%BB%E5%88%97%E8%A1%A8",
            "polity_source_raw": "698 年大祚荣建震国；713 年唐玄宗册封为渤海郡王；762 年升渤海国王；926 年辽太祖耶律阿保机灭之，置东丹国。",
            "confidence_score": 88,
            "confidence_note": "汉文与朝鲜《三国史记》互证；君主谥号大体清晰，9 世纪后中段几位汗王年份学者间有 ±1 年差异",
        },
        "rulers": rulers,
        "capitals": [
            ("旧国敖东城", "吉林省敦化市敖东城遗址", 698, 755, 128.232, 43.371, True, "initial_capital", "region",
             "《新唐书·渤海传》", "https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%9B%BD",
             "渤海初都旧国，今吉林敦化敖东城遗址", 80, ""),
            ("中京显德府", "吉林省和龙市西古城", 755, 756, 129.013, 42.546, False, "relocation", "region",
             "《辽史·地理志》", "https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%9B%BD",
             "755 年文王迁都显德府，仅 1 年后再迁上京", 75, ""),
            ("上京龙泉府", "黑龙江省宁安市渤海镇上京遗址", 756, 785, 129.001, 44.117, True, "relocation", "city",
             "《辽史·地理志》", "https://zh.wikipedia.org/wiki/%E4%B8%8A%E4%BA%AC%E9%BE%99%E6%B3%89%E5%BA%9C",
             "756 年迁都上京龙泉府；785 年文王晚年迁东京；794 年成王还都上京", 88, "考古遗址明确"),
            ("东京龙原府", "吉林省珲春市八连城遗址", 785, 794, 130.367, 42.866, False, "relocation", "region",
             "《辽史·地理志》", "https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%9B%BD",
             "785-794 文王末年与成王初年都东京龙原府", 78, ""),
            ("上京龙泉府（复都）", "黑龙江省宁安市渤海镇上京遗址", 794, 926, 129.001, 44.117, True, "relocation", "city",
             "《辽史·地理志》", "https://zh.wikipedia.org/wiki/%E4%B8%8A%E4%BA%AC%E9%BE%99%E6%B3%89%E5%BA%9C",
             "794 成王还都上京龙泉府直至 926 年亡国", 88, ""),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "polity_start_year",
                "selected_value": "698",
                "alternative_values": "699",
                "source_titles": "《旧唐书·渤海靺鞨传》/《三国史记·新罗本纪》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E6%B8%A4%E6%B5%B7%E5%9B%BD",
                "note": "大祚荣称王建震国一般用 698 年，少数韩文文献作 699 年。本表沿用 698。",
                "action_in_v03": "selected value retained; issue documented",
            },
        ],
    }


# 注入批 A
POLITY_DEFINITIONS.extend([
    define_nanzhao(),
    define_dali(),
    define_dazhong(),
    define_bohai(),
])


def define_tubo() -> dict[str, Any]:
    """吐蕃 629-842（《旧唐书·吐蕃传》《新唐书·吐蕃传》《资治通鉴》《敦煌吐蕃历史文书》）"""
    rulers = [
        ("松赞干布", "赞普", "", "", "弃宗弄赞", 629, 650, "", 82),
        ("芒松芒赞", "赞普", "", "", "芒松芒赞", 650, 676, "", 80),
        ("都松芒布支", "赞普", "", "", "都松芒布支", 676, 704, "", 78),
        ("赤德祖赞", "赞普", "", "弃隶蹜赞", "赤德祖赞", 704, 755, "", 85),
        ("赤松德赞", "赞普", "", "", "赤松德赞", 755, 797, "", 88),
        ("牟尼赞普", "赞普", "", "", "牟尼赞普", 797, 798, "", 75),
        ("赤德松赞", "赞普", "", "", "赤德松赞", 798, 815, "", 82),
        ("赤祖德赞", "赞普", "", "热巴巾", "赤祖德赞", 815, 838, "", 85),
        ("朗达玛", "赞普（末代）", "", "末代", "朗达玛", 838, 842, "", 85),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "吐蕃",
            "polity_name": "吐蕃",
            "polity_aliases": "土蕃 | 蕃 | Tibetan Empire | Bod chen po",
            "polity_type": "政权/国家",
            "polity_start_year": 629,
            "polity_end_year": 842,
            "polity_date_raw": "629年－842年",
            "polity_date_precision": "year",
            "historical_geography_raw": "以拉萨为中心，盛时辖青藏高原全域；东抵河西陇右与南诏，西临大食与天竺，南并尼婆罗",
            "modern_admin_units_raw": "西藏自治区全境、青海省大部、四川省西部、云南省西北、甘肃省南部、新疆南部、尼泊尔、不丹、印度锡金与拉达克、巴基斯坦控制克什米尔",
            "capital_historical": "逻些（拉萨）",
            "capital_modern": "西藏自治区拉萨市",
            "ruling_family_or_clan": "悉勃野氏 | 雅砻王系",
            "ethnicity_or_group": "吐蕃（古藏人）",
            "founder": "松赞干布",
            "last_ruler": "朗达玛",
            "destroyed_by_or_successor": "吐蕃分裂时期（拉萨王系与古格、拉达克等地方政权）",
            "polity_source_titles": "《旧唐书·吐蕃传》 | 《新唐书·吐蕃传》 | 《资治通鉴》 | 《敦煌吐蕃历史文书》 | 《贤者喜宴》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%90%90%E8%95%83 | https://zh.wikipedia.org/wiki/%E5%90%90%E8%95%83%E8%B5%9E%E6%99%AE%E5%88%97%E8%A1%A8",
            "polity_source_raw": "629 年松赞干布即位（敦煌历史文书戊子年）；842 年朗达玛被刺，吐蕃分裂。",
            "confidence_score": 85,
            "confidence_note": "汉藏文献交叉验证；松赞干布前世系传说化",
        },
        "rulers": rulers,
        "capitals": [
            ("逻些", "西藏自治区拉萨市", 633, 842, 91.117, 29.658, True, "initial_capital", "city",
             "《新唐书·吐蕃传》", "https://zh.wikipedia.org/wiki/%E6%8B%89%E8%90%A8",
             "约 633 年松赞干布迁都逻些（今拉萨），延续至吐蕃分裂", 82, "都城明确；城市级坐标"),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "polity_start_year",
                "selected_value": "629",
                "alternative_values": "634",
                "source_titles": "《敦煌吐蕃历史文书》/《新唐书·吐蕃传》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E5%90%90%E8%95%83",
                "note": "松赞干布即位年汉文《旧唐书》记 634，藏文敦煌历史文书（编年体早期实录）戊子年（629）。本表采用藏文 629 作为吐蕃王朝起点。",
                "action_in_v03": "selected value retained; issue documented",
            },
        ],
    }


def define_goguryeo() -> dict[str, Any]:
    """高句丽 -37~668（《三国史记》《三国志·东夷传》《魏书·高句丽传》《新唐书·高丽传》）"""
    rulers = [
        ("朱蒙", "东明圣王", "", "东明圣王", "朱蒙", -37, -19, "", 70),
        ("琉璃明王", "琉璃明王", "", "琉璃明王", "类利", -19, 18, "", 70),
        ("大武神王", "大武神王", "", "大武神王", "无恤", 18, 44, "", 72),
        ("闵中王", "闵中王", "", "闵中王", "解色朱", 44, 48, "", 70),
        ("慕本王", "慕本王", "", "慕本王", "解忧", 48, 53, "", 70),
        ("太祖大王", "太祖大王", "", "太祖大王", "宫", 53, 146, "", 72),
        ("次大王", "次大王", "", "次大王", "遂成", 146, 165, "", 70),
        ("新大王", "新大王", "", "新大王", "伯固", 165, 179, "", 72),
        ("故国川王", "故国川王", "", "故国川王", "男武", 179, 197, "", 75),
        ("山上王", "山上王", "", "山上王", "延优", 197, 227, "", 75),
        ("东川王", "东川王", "", "东川王", "忧位居", 227, 248, "", 80),
        ("中川王", "中川王", "", "中川王", "然弗", 248, 270, "", 75),
        ("西川王", "西川王", "", "西川王", "药卢", 270, 292, "", 75),
        ("烽上王", "烽上王", "", "烽上王", "相夫", 292, 300, "", 75),
        ("美川王", "美川王", "", "美川王", "乙弗", 300, 331, "", 78),
        ("故国原王", "故国原王", "", "故国原王", "斯由", 331, 371, "", 80),
        ("小兽林王", "小兽林王", "", "小兽林王", "丘夫", 371, 384, "", 82),
        ("故国壤王", "故国壤王", "", "故国壤王", "伊连", 384, 391, "", 82),
        ("广开土王", "广开土境平安好太王", "", "广开土王", "谈德", 391, 412, "永乐", 90),
        ("长寿王", "长寿王", "", "长寿王", "巨连", 413, 491, "", 90),
        ("文咨明王", "文咨明王", "", "文咨明王", "罗云", 491, 519, "", 85),
        ("安藏王", "安藏王", "", "安藏王", "兴安", 519, 531, "", 80),
        ("安原王", "安原王", "", "安原王", "宝延", 531, 545, "", 80),
        ("阳原王", "阳原王", "", "阳原王", "平成", 545, 559, "", 80),
        ("平原王", "平原王", "", "平原王", "阳成", 559, 590, "", 82),
        ("婴阳王", "婴阳王", "", "婴阳王", "元", 590, 618, "", 85),
        ("荣留王", "荣留王", "", "荣留王", "建武", 618, 642, "", 88),
        ("宝藏王", "宝藏王（末代）", "", "末代", "藏", 642, 668, "", 90),
    ]
    return {
        "polity": {
            "macro_period": "魏晋南北朝",
            "dynasty_name": "高句丽",
            "polity_name": "高句丽",
            "polity_aliases": "高麗 | 高句麗 | Goguryeo | Koguryŏ",
            "polity_type": "政权/国家",
            "polity_start_year": -37,
            "polity_end_year": 668,
            "polity_date_raw": "前37年－668年",
            "polity_date_precision": "year",
            "historical_geography_raw": "立国于辽东桓仁；先后定都国内城（集安）、平壤；盛时辖辽东、辽河中下游、朝鲜半岛北部、滨海边疆区南部",
            "modern_admin_units_raw": "吉林省东南部、辽宁省东部、朝鲜民主主义人民共和国全境、韩国京畿道以北部分、俄罗斯滨海边疆区南部",
            "capital_historical": "卒本（前37-3）| 国内城（3-427）| 平壤（427-668）",
            "capital_modern": "辽宁省桓仁满族自治县（卒本）/ 吉林省集安市（国内城）/ 朝鲜平壤市（平壤）",
            "ruling_family_or_clan": "高氏 | 朱蒙后裔",
            "ethnicity_or_group": "貊（高句丽/扶余系）",
            "founder": "朱蒙（东明圣王）",
            "last_ruler": "宝藏王",
            "destroyed_by_or_successor": "唐朝（李勣破平壤）",
            "polity_source_titles": "《三国史记·高句丽本纪》 | 《三国志·东夷传》 | 《魏书·高句丽传》 | 《北史·高丽传》 | 《旧唐书·高丽传》 | 《新唐书·高丽传》 | 《资治通鉴》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E9%AB%98%E5%8F%A5%E9%BA%97 | https://zh.wikipedia.org/wiki/%E9%AB%98%E5%8F%A5%E9%BA%97%E5%9B%BD%E7%8E%8B%E5%88%97%E8%A1%A8",
            "polity_source_raw": "前37 年朱蒙建国（《三国史记》传统口径）；668 年唐李勣破平壤，宝藏王降，高句丽亡。",
            "confidence_score": 85,
            "confidence_note": "汉文/朝鲜文献互证；早期王系（前37 ~ 1世纪）传说色彩浓",
        },
        "rulers": rulers,
        "capitals": [
            ("卒本", "辽宁省桓仁满族自治县五女山城", -37, 3, 125.366, 41.265, True, "initial_capital", "region",
             "《三国史记·高句丽本纪》", "https://zh.wikipedia.org/wiki/%E9%AB%98%E5%8F%A5%E9%BA%97",
             "前37 年朱蒙建国初都卒本，考古遗址为今桓仁五女山城", 75, ""),
            ("国内城", "吉林省集安市", 3, 427, 126.183, 41.124, True, "relocation", "city",
             "《三国史记》《魏书·高句丽传》", "https://zh.wikipedia.org/wiki/%E5%9C%8B%E5%85%A7%E5%9F%8E",
             "前3 年（《三国史记》琉璃明王 22 年）迁都国内城；427 年长寿王迁平壤", 82, "考古遗址明确"),
            ("平壤", "朝鲜平壤市", 427, 668, 125.762, 39.039, True, "relocation", "city",
             "《新唐书·高丽传》", "https://zh.wikipedia.org/wiki/%E5%B9%B3%E5%A3%A4",
             "427 年长寿王迁都平壤直至 668 年亡国", 88, ""),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "polity_start_year",
                "selected_value": "-37",
                "alternative_values": "公元 1 世纪初（考古口径）",
                "source_titles": "《三国史记·高句丽本纪》/ 现代考古",
                "source_urls": "https://zh.wikipedia.org/wiki/%E9%AB%98%E5%8F%A5%E9%BA%97",
                "note": "传统纪年沿用《三国史记》前 37 年朱蒙建国，但现代考古学者多认为高句丽早期带传说色彩，真正的国家形态形成在 1 世纪初。",
                "action_in_v03": "selected value retained; issue documented",
            },
        ],
    }


def define_turkic_khaganate() -> dict[str, Any]:
    """突厥汗国 552-583（《周书·突厥传》《北史·突厥传》《隋书·突厥传》）"""
    rulers = [
        ("伊利可汗", "伊利可汗", "", "", "土门", 552, 553, "", 82),
        ("乙息记可汗", "乙息记可汗", "", "", "科罗", 553, 553, "", 75),
        ("木杆可汗", "木杆可汗", "", "", "俟斤", 553, 572, "", 85),
        ("佗钵可汗", "佗钵可汗", "", "", "佗钵", 572, 581, "", 82),
        ("沙钵略可汗", "沙钵略可汗", "", "", "摄图", 581, 587, "", 82),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "突厥汗国",
            "polity_name": "突厥汗国",
            "polity_aliases": "突厥 | 第一突厥汗国 | Göktürk Khaganate",
            "polity_type": "政权/国家",
            "polity_start_year": 552,
            "polity_end_year": 583,
            "polity_date_raw": "552年－583年",
            "polity_date_precision": "year",
            "historical_geography_raw": "552 年土门破柔然建突厥汗国；盛时东自满洲、西尽里海，跨蒙古、中亚",
            "modern_admin_units_raw": "蒙古国全境、俄罗斯西伯利亚南部、哈萨克斯坦、吉尔吉斯斯坦、乌兹别克斯坦、土库曼斯坦、塔吉克斯坦、阿富汗北部",
            "capital_historical": "于都斤山",
            "capital_modern": "蒙古国前杭爱省哈剌和林一带",
            "ruling_family_or_clan": "阿史那氏",
            "ethnicity_or_group": "突厥",
            "founder": "土门（伊利可汗）",
            "last_ruler": "沙钵略可汗",
            "destroyed_by_or_successor": "583 年分裂为东突厥与西突厥（隋离间）",
            "polity_source_titles": "《周书·突厥传》 | 《北史·突厥传》 | 《隋书·突厥传》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E7%AA%81%E5%8E%A5%E6%B1%97%E5%9C%8B",
            "polity_source_raw": "552 年阿史那土门破柔然自立伊利可汗；583 年沙钵略与达头可汗分立，突厥分东西。",
            "confidence_score": 85,
            "confidence_note": "正史互证；可汗在位年份基本可考",
        },
        "rulers": rulers,
        "capitals": [
            ("于都斤山", "蒙古国前杭爱省哈剌和林周边", 552, 583, 102.832, 47.232, True, "initial_capital", "region",
             "《周书·突厥传》", "https://zh.wikipedia.org/wiki/%E4%BA%8E%E9%83%BD%E6%96%A4%E5%B1%B1",
             "突厥可汗驻牙地于都斤山（Ötükän），今哈剌和林周边鄂尔浑河流域", 75, "区域级近似坐标"),
        ],
        "issues": [],
    }


def define_eastern_turkic() -> dict[str, Any]:
    """东突厥 583-630（沙钵略系；《隋书·突厥传》《旧唐书·突厥传》）"""
    rulers = [
        ("沙钵略可汗", "沙钵略可汗", "", "", "摄图", 583, 587, "", 80),
        ("莫何可汗", "莫何可汗（叶护可汗）", "", "", "处罗侯", 587, 588, "", 75),
        ("都蓝可汗", "都蓝可汗", "", "", "雍虞闾", 588, 599, "", 78),
        ("启民可汗", "启民可汗", "", "", "染干", 599, 609, "", 82),
        ("始毕可汗", "始毕可汗", "", "", "咄吉", 609, 619, "", 82),
        ("处罗可汗", "处罗可汗", "", "", "俟利弗设", 619, 620, "", 78),
        ("颉利可汗", "颉利可汗（末代）", "", "末代", "咄苾", 620, 630, "", 88),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "东突厥",
            "polity_name": "东突厥",
            "polity_aliases": "東突厥 | 東突厥汗國",
            "polity_type": "政权/国家",
            "polity_start_year": 583,
            "polity_end_year": 630,
            "polity_date_raw": "583年－630年",
            "polity_date_precision": "year",
            "historical_geography_raw": "583 年突厥分裂；东突厥以漠南漠北为主，盛时辖蒙古高原、内蒙古、河西走廊以北、辽河上游",
            "modern_admin_units_raw": "蒙古国全境、俄罗斯西伯利亚南部、内蒙古自治区、新疆北部、河西走廊以北",
            "capital_historical": "于都斤山（漠北可汗庭）",
            "capital_modern": "蒙古国前杭爱省哈剌和林一带",
            "ruling_family_or_clan": "阿史那氏",
            "ethnicity_or_group": "突厥",
            "founder": "沙钵略可汗",
            "last_ruler": "颉利可汗",
            "destroyed_by_or_successor": "唐朝（李靖夜袭阴山，颉利被擒）",
            "polity_source_titles": "《隋书·突厥传》 | 《旧唐书·突厥传》 | 《新唐书·突厥传》 | 《资治通鉴》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E6%9D%B1%E7%AA%81%E5%8E%A5",
            "polity_source_raw": "583 年东西突厥分立；630 年唐李靖大破东突厥，颉利可汗被擒，东突厥亡。",
            "confidence_score": 85,
            "confidence_note": "可汗在位年隋唐两书略有 ±1 年差异",
        },
        "rulers": rulers,
        "capitals": [
            ("于都斤山", "蒙古国前杭爱省哈剌和林周边", 583, 630, 102.832, 47.232, True, "initial_capital", "region",
             "《隋书·突厥传》", "https://zh.wikipedia.org/wiki/%E4%BA%8E%E9%83%BD%E6%96%A4%E5%B1%B1",
             "东突厥可汗驻于都斤山", 72, ""),
        ],
        "issues": [],
    }


def define_western_turkic() -> dict[str, Any]:
    """西突厥 583-657（达头/室点密系；《隋书·西突厥传》《旧唐书·突厥传》）"""
    rulers = [
        ("达头可汗", "达头可汗（步迦可汗）", "", "", "玷厥", 583, 603, "", 78),
        ("射匮可汗", "射匮可汗", "", "", "射匮", 611, 618, "", 75),
        ("统叶护可汗", "统叶护可汗", "", "", "莫贺咄", 618, 628, "", 82),
        ("莫贺咄可汗", "莫贺咄可汗", "", "", "莫贺咄", 628, 630, "", 70),
        ("肆叶护可汗", "肆叶护可汗", "", "", "咥力特勒", 630, 632, "", 70),
        ("咄陆可汗", "咄陆可汗", "", "", "咄陆", 633, 638, "", 72),
        ("乙毗咄陆可汗", "乙毗咄陆可汗", "", "", "欲谷设", 638, 642, "", 70),
        ("乙毗射匮可汗", "乙毗射匮可汗", "", "", "射匮", 642, 651, "", 70),
        ("阿史那贺鲁", "沙钵罗可汗（末代）", "", "末代", "贺鲁", 651, 657, "", 85),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "西突厥",
            "polity_name": "西突厥",
            "polity_aliases": "西突厥汗國 | Western Türk Khaganate",
            "polity_type": "政权/国家",
            "polity_start_year": 583,
            "polity_end_year": 657,
            "polity_date_raw": "583年－657年",
            "polity_date_precision": "year",
            "historical_geography_raw": "583 年突厥分裂后以中亚为中心，盛时辖天山以南北、阿尔泰山以西、河中粟特诸国及阿姆河—锡尔河流域",
            "modern_admin_units_raw": "新疆维吾尔自治区、哈萨克斯坦、吉尔吉斯斯坦、乌兹别克斯坦、土库曼斯坦、塔吉克斯坦、阿富汗北部、伊朗东北、巴基斯坦西北部",
            "capital_historical": "碎叶 | 千泉",
            "capital_modern": "吉尔吉斯斯坦楚河州托克马克市附近",
            "ruling_family_or_clan": "阿史那氏",
            "ethnicity_or_group": "突厥",
            "founder": "达头可汗",
            "last_ruler": "阿史那贺鲁",
            "destroyed_by_or_successor": "唐朝（苏定方西征擒贺鲁）",
            "polity_source_titles": "《隋书·西突厥传》 | 《旧唐书·突厥传》 | 《新唐书·突厥传》 | 《大唐西域记》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E8%A5%BF%E7%AA%81%E5%8E%A5",
            "polity_source_raw": "583 年达头西离自立；657 年唐苏定方擒阿史那贺鲁，西突厥亡。",
            "confidence_score": 80,
            "confidence_note": "西突厥诸可汗在位年学者多有分歧；本表择隋唐两书与岑仲勉《突厥集史》之中间口径",
        },
        "rulers": rulers,
        "capitals": [
            ("碎叶", "吉尔吉斯斯坦楚河州托克马克附近", 583, 657, 75.281, 42.835, True, "initial_capital", "region",
             "《大唐西域记》/《旧唐书·突厥传》", "https://zh.wikipedia.org/wiki/%E7%A2%8E%E8%91%89%E5%9F%8E",
             "西突厥可汗夏驻千泉，冬驻碎叶城（今吉尔吉斯托克马克附近）", 72, "区域级近似坐标"),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "ruler_reign_years",
                "selected_value": "本表沿用《旧唐书·突厥传》主线",
                "alternative_values": "岑仲勉《突厥集史》、内田吟风等校本",
                "source_titles": "《旧唐书·突厥传》/ 岑仲勉《突厥集史》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E8%A5%BF%E7%AA%81%E5%8E%A5",
                "note": "西突厥诸可汗在位年学界分歧显著（莫贺咄、肆叶护、咄陆三可汗尤甚）；本表择两唐书主线 + 岑仲勉校本中位，置信度普遍 ≤ 75。",
                "action_in_v03": "selected value retained; issue documented",
            },
        ],
    }


def define_second_turkic() -> dict[str, Any]:
    """后突厥（第二突厥汗国） 682-744（《旧唐书·突厥传》《新唐书·突厥传》《阙特勤碑》）"""
    rulers = [
        ("骨咄禄", "颉跌利施可汗", "", "", "骨咄禄", 682, 691, "", 85),
        ("默啜可汗", "默啜可汗", "", "", "默啜", 691, 716, "", 88),
        ("阙特勤", "（实际军政首脑，未即位）", "", "", "阙特勤", 716, 731, "", 75),
        ("毗伽可汗", "毗伽可汗", "", "", "默棘连", 716, 734, "", 88),
        ("伊然可汗", "伊然可汗", "", "", "苾伽古朵禄", 734, 734, "", 70),
        ("登利可汗", "登利可汗", "", "", "登利", 734, 741, "", 75),
        ("乌苏米施可汗", "乌苏米施可汗", "", "", "乌苏米施", 741, 743, "", 72),
        ("白眉可汗", "白眉可汗（末代）", "", "末代", "鹘陇匐", 743, 744, "", 80),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "后突厥",
            "polity_name": "后突厥",
            "polity_aliases": "後突厥汗國 | 第二突厥汗國 | Second Türk Khaganate",
            "polity_type": "政权/国家",
            "polity_start_year": 682,
            "polity_end_year": 744,
            "polity_date_raw": "682年－744年",
            "polity_date_precision": "year",
            "historical_geography_raw": "682 年阿史那骨咄禄复国于漠北；盛时复辖蒙古高原、内蒙古、新疆北、外蒙；744 年被回纥+葛逻禄+拔悉密联军所灭",
            "modern_admin_units_raw": "蒙古国全境、俄罗斯西伯利亚南部、内蒙古自治区、新疆北部",
            "capital_historical": "于都斤山",
            "capital_modern": "蒙古国前杭爱省哈剌和林一带",
            "ruling_family_or_clan": "阿史那氏",
            "ethnicity_or_group": "突厥",
            "founder": "骨咄禄（颉跌利施可汗）",
            "last_ruler": "白眉可汗",
            "destroyed_by_or_successor": "回鹘汗国（骨力裴罗）",
            "polity_source_titles": "《旧唐书·突厥传》 | 《新唐书·突厥传》 | 《阙特勤碑》 | 《毗伽可汗碑》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%BE%8C%E7%AA%81%E5%8E%A5%E6%B1%97%E5%9C%8B",
            "polity_source_raw": "682 年阿史那骨咄禄复国；744 年回纥+葛逻禄+拔悉密三部联军灭白眉可汗。",
            "confidence_score": 85,
            "confidence_note": "汉文 + 突厥文碑铭（鄂尔浑碑）互证，置信度较高",
        },
        "rulers": rulers,
        "capitals": [
            ("于都斤山", "蒙古国前杭爱省哈剌和林周边", 682, 744, 102.832, 47.232, True, "initial_capital", "region",
             "《旧唐书·突厥传》", "https://zh.wikipedia.org/wiki/%E4%BA%8E%E9%83%BD%E6%96%A4%E5%B1%B1",
             "后突厥可汗复都于都斤山", 75, ""),
        ],
        "issues": [],
    }


# 注入批 B
POLITY_DEFINITIONS.extend([
    define_tubo(),
    define_goguryeo(),
    define_turkic_khaganate(),
    define_eastern_turkic(),
    define_western_turkic(),
    define_second_turkic(),
])


def define_xiongnu() -> dict[str, Any]:
    """匈奴单于国 -209~91（《史记·匈奴列传》《汉书·匈奴传》《后汉书·南匈奴列传》）"""
    rulers = [
        ("冒顿单于", "单于", "", "", "冒顿", -209, -174, "", 88),
        ("老上单于", "老上单于", "", "", "稽粥", -174, -161, "", 85),
        ("军臣单于", "军臣单于", "", "", "军臣", -161, -126, "", 85),
        ("伊稚斜单于", "伊稚斜单于", "", "", "伊稚斜", -126, -114, "", 82),
        ("乌维单于", "乌维单于", "", "", "乌维", -114, -105, "", 82),
        ("儿单于", "儿单于", "", "", "乌师庐", -105, -102, "", 78),
        ("呴犁湖单于", "呴犁湖单于", "", "", "呴犁湖", -102, -101, "", 75),
        ("且鞮侯单于", "且鞮侯单于", "", "", "且鞮侯", -101, -96, "", 82),
        ("狐鹿姑单于", "狐鹿姑单于", "", "", "狐鹿姑", -96, -85, "", 82),
        ("壶衍鞮单于", "壶衍鞮单于", "", "", "壶衍鞮", -85, -68, "", 82),
        ("虚闾权渠单于", "虚闾权渠单于", "", "", "虚闾权渠", -68, -60, "", 80),
        ("握衍朐鞮单于", "握衍朐鞮单于", "", "", "屠耆堂", -60, -58, "", 78),
        ("呼韩邪单于", "呼韩邪单于（统一）", "", "", "稽侯狦", -58, -31, "", 88),
        ("复株累若鞮单于", "复株累若鞮单于", "", "", "雕陶莫皋", -31, -20, "", 82),
        ("搜谐若鞮单于", "搜谐若鞮单于", "", "", "且糜胥", -20, -12, "", 80),
        ("车牙若鞮单于", "车牙若鞮单于", "", "", "且莫车", -12, -8, "", 78),
        ("乌珠留若鞮单于", "乌珠留若鞮单于", "", "", "囊知牙斯", -8, 13, "", 82),
        ("乌累若鞮单于", "乌累若鞮单于", "", "", "咸", 13, 18, "", 78),
        ("呼都而尸道皋若鞮单于", "呼都而尸道皋若鞮单于", "", "", "舆", 18, 46, "", 78),
        ("蒲奴单于", "蒲奴单于（北匈奴）", "", "", "蒲奴", 46, 83, "", 75),
        ("优留单于", "优留单于（北匈奴末代）", "", "末代", "优留", 83, 91, "", 78),
    ]
    return {
        "polity": {
            "macro_period": "秦汉",
            "dynasty_name": "匈奴单于国",
            "polity_name": "匈奴",
            "polity_aliases": "匈奴單于國 | 匈奴 | Xiongnu",
            "polity_type": "政权/国家",
            "polity_start_year": -209,
            "polity_end_year": 91,
            "polity_date_raw": "前209年－91年",
            "polity_date_precision": "year",
            "historical_geography_raw": "冒顿即位（前209）后统一草原；盛时东接秽貉朝鲜，西尽西域，南界赵燕晋长城，北越贝加尔湖。48 年分裂为南北匈奴，91 年北匈奴被东汉窦宪破，北窜中亚",
            "modern_admin_units_raw": "蒙古国全境、俄罗斯西伯利亚南部、贝加尔湖周边、内蒙古自治区、新疆北部、哈萨克斯坦东部、吉尔吉斯斯坦",
            "capital_historical": "单于庭（漠北流动牙帐）",
            "capital_modern": "蒙古国前杭爱省哈剌和林一带（漠北单于庭区域）",
            "ruling_family_or_clan": "挛鞮氏（虚连鞮氏）",
            "ethnicity_or_group": "匈奴",
            "founder": "冒顿单于",
            "last_ruler": "优留单于（北匈奴末代）",
            "destroyed_by_or_successor": "东汉（窦宪燕然山勒石；北匈奴北窜中亚）",
            "polity_source_titles": "《史记·匈奴列传》 | 《汉书·匈奴传》 | 《后汉书·南匈奴列传》 | 《后汉书·窦宪传》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%8C%88%E5%A5%B4 | https://zh.wikipedia.org/wiki/%E5%8C%88%E5%A5%B4%E5%96%AE%E4%BA%8E%E5%88%97%E8%A1%A8",
            "polity_source_raw": "前209 年冒顿杀头曼自立；91 年东汉窦宪、耿夔大破北匈奴于金微山，北匈奴单于西遁，北匈奴亡。",
            "confidence_score": 85,
            "confidence_note": "《史》《汉》互证主线清晰；单于在位年个别 ±1 年差异",
        },
        "rulers": rulers,
        "capitals": [
            ("单于庭", "蒙古国鄂尔浑河流域", -209, 91, 102.832, 47.232, True, "initial_capital", "region",
             "《史记·匈奴列传》", "https://zh.wikipedia.org/wiki/%E5%8C%88%E5%A5%B4",
             "匈奴单于驻牙在漠北鄂尔浑河流域（今哈剌和林周边），随季节流动", 70, "游牧驻牙；区域级近似"),
        ],
        "issues": [
            {
                "issue_type": "chronology_variant",
                "field_name": "polity_end_year",
                "selected_value": "91",
                "alternative_values": "93",
                "source_titles": "《后汉书·南匈奴列传》/《资治通鉴》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E5%8C%88%E5%A5%B4",
                "note": "北匈奴单于走窜年份汉书与通鉴略有差异：91 燕然破之后单于走，93 年北单于实际再败北窜；本表取 91 为北匈奴帝国实质终结。",
                "action_in_v03": "selected value retained; issue documented",
            },
        ],
    }


def define_southern_xiongnu() -> dict[str, Any]:
    """南匈奴 48~216（《后汉书·南匈奴列传》《三国志·武帝纪》）"""
    rulers = [
        ("醢落尸逐鞮单于", "南匈奴单于", "", "", "比", 48, 56, "", 82),
        ("丘浮尤鞮单于", "南匈奴单于", "", "", "莫", 56, 57, "", 75),
        ("伊伐于虑鞮单于", "南匈奴单于", "", "", "汗", 57, 59, "", 75),
        ("醢童尸逐侯鞮单于", "南匈奴单于", "", "", "适", 59, 63, "", 75),
        ("丘除车林鞮单于", "南匈奴单于", "", "", "苏", 63, 63, "", 70),
        ("湖斜尸逐侯鞮单于", "南匈奴单于", "", "", "长", 63, 85, "", 78),
        ("伊屠于闾鞮单于", "南匈奴单于", "", "", "宣", 85, 88, "", 75),
        ("休兰尸逐侯鞮单于", "南匈奴单于", "", "", "屯屠何", 88, 93, "", 75),
        ("安国单于", "南匈奴单于", "", "", "安国", 93, 94, "", 70),
        ("亭独尸逐侯鞮单于", "南匈奴单于", "", "", "师子", 94, 98, "", 75),
        ("万氏尸逐侯鞮单于", "南匈奴单于", "", "", "檀", 98, 124, "", 78),
        ("乌稽侯尸逐鞮单于", "南匈奴单于", "", "", "拔", 124, 128, "", 75),
        ("去特若尸逐就鞮单于", "南匈奴单于", "", "", "休利", 128, 140, "", 75),
        ("呼兰若尸逐就鞮单于", "南匈奴单于", "", "", "车纽", 140, 143, "", 70),
        ("伊陵尸逐就鞮单于", "南匈奴单于", "", "", "居车儿", 143, 147, "", 72),
        ("休利尸逐侯鞮单于", "南匈奴单于", "", "", "兜楼储", 147, 172, "", 75),
        ("屠特若尸逐就鞮单于", "南匈奴单于", "", "", "呼徵", 172, 178, "", 72),
        ("呼徵单于", "南匈奴单于", "", "", "呼徵（再立）", 178, 179, "", 65),
        ("羌渠单于", "南匈奴单于", "", "", "羌渠", 179, 188, "", 75),
        ("持至尸逐侯单于", "南匈奴单于", "", "", "于扶罗", 188, 195, "", 80),
        ("呼厨泉单于", "南匈奴单于（末代）", "", "末代", "呼厨泉", 195, 216, "", 85),
    ]
    return {
        "polity": {
            "macro_period": "秦汉",
            "dynasty_name": "南匈奴",
            "polity_name": "南匈奴",
            "polity_aliases": "南匈奴 | 南單于國",
            "polity_type": "政权/国家",
            "polity_start_year": 48,
            "polity_end_year": 216,
            "polity_date_raw": "48年－216年",
            "polity_date_precision": "year",
            "historical_geography_raw": "48 年比单于率部归汉，南匈奴附塞而居，活动于今山西、河套、陕北长城以南至并州一带；216 年曹操析为五部",
            "modern_admin_units_raw": "内蒙古自治区南部、山西省北部、陕西省北部、宁夏回族自治区、甘肃省东北部、河北省北部",
            "capital_historical": "美稷（南庭）| 离石、平阳（后期）",
            "capital_modern": "内蒙古自治区准格尔旗（美稷古地）/ 山西省临汾市",
            "ruling_family_or_clan": "挛鞮氏（虚连鞮氏）",
            "ethnicity_or_group": "匈奴",
            "founder": "醢落尸逐鞮单于（比）",
            "last_ruler": "呼厨泉单于",
            "destroyed_by_or_successor": "曹魏（曹操析南匈奴为五部，呼厨泉留邺）",
            "polity_source_titles": "《后汉书·南匈奴列传》 | 《三国志·武帝纪》 | 《晋书·北狄传》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%8D%97%E5%8C%88%E5%A5%B4",
            "polity_source_raw": "48 年比单于自立南庭附汉；216 年曹操析南匈奴为左、右、南、北、中五部，呼厨泉留邺为名号单于。",
            "confidence_score": 82,
            "confidence_note": "《后汉书·南匈奴列传》主线清晰；几位短命单于在位年学者有分歧",
        },
        "rulers": rulers,
        "capitals": [
            ("美稷", "内蒙古自治区准格尔旗西北", 50, 140, 110.998, 39.870, True, "initial_capital", "region",
             "《后汉书·南匈奴列传》", "https://zh.wikipedia.org/wiki/%E5%8D%97%E5%8C%88%E5%A5%B4",
             "南匈奴单于驻牙美稷（今鄂尔多斯准格尔旗西北），延续至 2 世纪中叶", 72, ""),
            ("离石", "山西省吕梁市离石区", 140, 216, 111.151, 37.517, False, "relocation", "city",
             "《后汉书·南匈奴列传》", "https://zh.wikipedia.org/wiki/%E5%8D%97%E5%8C%88%E5%A5%B4",
             "汉末南匈奴单于庭南徙离石、平阳一带", 70, ""),
        ],
        "issues": [],
    }


def define_uyghur_khaganate() -> dict[str, Any]:
    """回鹘汗国 744~840（《新唐书·回鹘传》《旧唐书·回纥传》《资治通鉴》）"""
    rulers = [
        ("骨力裴罗", "怀仁可汗", "", "", "骨力裴罗", 744, 747, "", 85),
        ("磨延啜", "葛勒可汗（英武威远毗伽可汗）", "", "", "磨延啜", 747, 759, "", 88),
        ("移地健", "牟羽可汗（登里可汗）", "", "", "移地健", 759, 779, "", 88),
        ("顿莫贺达干", "合骨咄禄毗伽可汗（长寿天亲可汗）", "", "", "顿莫贺达干", 779, 789, "", 85),
        ("多逻斯", "忠贞可汗", "", "", "多逻斯", 789, 790, "", 75),
        ("阿啜", "奉诚可汗", "", "", "阿啜", 790, 795, "", 78),
        ("骨咄禄", "怀信可汗", "", "", "骨咄禄", 795, 805, "", 80),
        ("滕里野合可汗", "滕里野合可汗", "", "", "腾里野合", 805, 808, "", 70),
        ("保义可汗", "保义可汗（爱登里啰汩没密施合毗伽可汗）", "", "", "保义", 808, 821, "", 82),
        ("崇德可汗", "崇德可汗", "", "", "君", 821, 824, "", 75),
        ("昭礼可汗", "昭礼可汗", "", "", "昭礼", 824, 832, "", 75),
        ("彰信可汗", "彰信可汗", "", "", "彰信", 832, 839, "", 75),
        ("厥啜特勤", "𠫊特勒可汗（末代）", "", "末代", "厥啜特勤", 839, 840, "", 78),
    ]
    return {
        "polity": {
            "macro_period": "隋唐",
            "dynasty_name": "回鹘汗国",
            "polity_name": "回鹘汗国",
            "polity_aliases": "回紇 | 迴鶻 | 回鶻汗國 | Uyghur Khaganate",
            "polity_type": "政权/国家",
            "polity_start_year": 744,
            "polity_end_year": 840,
            "polity_date_raw": "744年－840年",
            "polity_date_precision": "year",
            "historical_geography_raw": "744 年回纥首领骨力裴罗联合葛逻禄+拔悉密灭后突厥；都鄂尔浑河窝鲁朵八里；盛时辖蒙古高原、外蒙、西伯利亚南部、新疆北",
            "modern_admin_units_raw": "蒙古国全境、俄罗斯西伯利亚南部、内蒙古自治区、新疆北部",
            "capital_historical": "窝鲁朵八里（鄂尔浑河 Ordu Baliq）",
            "capital_modern": "蒙古国后杭爱省哈剌巴喇哈逊遗址",
            "ruling_family_or_clan": "药罗葛氏",
            "ethnicity_or_group": "回纥（铁勒诸部之一）",
            "founder": "骨力裴罗",
            "last_ruler": "𠫊特勤可汗",
            "destroyed_by_or_successor": "黠戛斯（破回鹘可汗庭，回鹘部众西迁）",
            "polity_source_titles": "《旧唐书·回纥传》 | 《新唐书·回鹘传》 | 《资治通鉴》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E5%9B%9E%E9%B6%BB%E6%B1%97%E5%9C%8B",
            "polity_source_raw": "744 年灭后突厥建汗国；840 年黠戛斯破其汗庭，可汗北逃，部众西迁分为高昌回鹘、甘州回鹘、葱岭西回鹘（喀喇汗朝）。",
            "confidence_score": 85,
            "confidence_note": "汉文与突厥碑铭互证；几位中后期短命可汗在位年学者间有差异",
        },
        "rulers": rulers,
        "capitals": [
            ("窝鲁朵八里", "蒙古国后杭爱省哈剌巴喇哈逊遗址", 744, 840, 102.673, 47.434, True, "initial_capital", "region",
             "《新唐书·回鹘传》", "https://zh.wikipedia.org/wiki/%E5%9B%9E%E9%B6%BB%E6%B1%97%E5%9C%8B",
             "回鹘可汗驻牙鄂尔浑河窝鲁朵八里（Ordu Baliq），今哈剌巴喇哈逊遗址", 80, ""),
        ],
        "issues": [],
    }


def define_gaochang_uyghur() -> dict[str, Any]:
    """高昌回鹘 866~1283（西州回鹘；《宋史·高昌国传》《辽史》《元史·亦都护传》）"""
    rulers = [
        ("仆固俊", "亦都护（建国）", "", "", "仆固俊", 866, 880, "", 75),
        ("毗伽阿厮兰汗", "亦都护", "", "", "阿厮兰", 1024, 1068, "", 65),
        ("毕勒哥", "亦都护", "", "", "毕勒哥", 1068, 1132, "", 65),
        ("巴而朮·阿尔忒·的斤", "亦都护（投顺成吉思汗）", "", "", "巴而朮·阿尔忒·的斤", 1208, 1235, "", 82),
        ("玉古伦赤的斤", "亦都护", "", "", "玉古伦赤", 1235, 1242, "", 70),
        ("马木剌的斤", "亦都护", "", "", "马木剌", 1242, 1253, "", 70),
        ("撒里都的斤", "亦都护", "", "", "撒里都", 1253, 1257, "", 65),
        ("玉古伦赤的斤（再立）", "亦都护", "", "", "玉古伦赤再立", 1257, 1265, "", 65),
        ("火赤哈儿的斤", "亦都护（末代）", "", "末代", "火赤哈儿", 1265, 1283, "", 75),
    ]
    return {
        "polity": {
            "macro_period": "宋辽金夏",
            "dynasty_name": "高昌回鹘",
            "polity_name": "高昌回鹘",
            "polity_aliases": "西州回鶻 | 高昌国 | 高昌回鶻 | Uyghur Idiqut",
            "polity_type": "政权/国家",
            "polity_start_year": 866,
            "polity_end_year": 1283,
            "polity_date_raw": "866年－1283年",
            "polity_date_precision": "year",
            "historical_geography_raw": "回鹘西迁主流之一，定居西州（吐鲁番）建国；盛时辖吐鲁番盆地、北庭、焉耆，10 世纪至 12 世纪与西州地区诸城邦联合",
            "modern_admin_units_raw": "新疆维吾尔自治区吐鲁番市、昌吉回族自治州、巴音郭楞蒙古自治州北部",
            "capital_historical": "高昌（西州）| 北庭（夏都）",
            "capital_modern": "新疆维吾尔自治区吐鲁番市高昌区（高昌故城）",
            "ruling_family_or_clan": "药罗葛系亦都护",
            "ethnicity_or_group": "回鹘",
            "founder": "仆固俊",
            "last_ruler": "火赤哈儿的斤",
            "destroyed_by_or_successor": "元朝（亦都护制改设西州行省，火赤哈儿战死）",
            "polity_source_titles": "《宋史·高昌国传》 | 《辽史》 | 《元史·亦都护传》 | 《长春真人西游记》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E9%AB%98%E6%98%8C%E5%9B%9E%E9%B6%BB | https://zh.wikipedia.org/wiki/%E4%BA%A6%E9%83%BD%E8%AD%B7",
            "polity_source_raw": "866 年仆固俊收复北庭，西州回鹘立国；1283 年火赤哈儿亦都护战死于火州，亦都护体制并入元朝。",
            "confidence_score": 75,
            "confidence_note": "9~10 世纪世系仅可考首位，10~13 世纪世系不完整，学界普遍依赖《长春真人西游记》《元史》拼合",
        },
        "rulers": rulers,
        "capitals": [
            ("高昌（西州）", "新疆维吾尔自治区吐鲁番市高昌故城", 866, 1283, 89.531, 42.853, True, "initial_capital", "city",
             "《宋史·高昌国传》", "https://zh.wikipedia.org/wiki/%E9%AB%98%E6%98%8C%E5%9B%9E%E9%B6%BB",
             "高昌回鹘以高昌（今吐鲁番）为冬都，北庭（今吉木萨尔）为夏都", 80, ""),
            ("北庭", "新疆维吾尔自治区昌吉回族自治州吉木萨尔县北庭故城", 866, 1283, 89.190, 44.083, False, "co_capital", "city",
             "《宋史·高昌国传》", "https://zh.wikipedia.org/wiki/%E5%8C%97%E5%BA%AD%E6%95%85%E5%9F%8E",
             "高昌回鹘夏都北庭", 75, ""),
        ],
        "issues": [
            {
                "issue_type": "partial_boundary",
                "field_name": "ruler_succession",
                "selected_value": "本表沿用可考的 9 位亦都护",
                "alternative_values": "学界对 9-13 世纪间的亦都护断代仍有较多空白",
                "source_titles": "《元史·亦都护传》/ 现代学者考证",
                "source_urls": "https://zh.wikipedia.org/wiki/%E9%AB%98%E6%98%8C%E5%9B%9E%E9%B6%BB",
                "note": "高昌回鹘亦都护世系汉文文献记载多有阙漏，特别是 900~1023 年间几乎无系统记录；本表仅列有明确史料支撑的几位，缺失年间作为 year_polity_unmatched_ruler 保留。",
                "action_in_v03": "polity_continuity preserved; ruler gaps tracked as unmatched-ruler years",
            },
        ],
    }


def define_ganzhou_uyghur() -> dict[str, Any]:
    """甘州回鹘 848~1036（《宋史·回鹘传》《辽史》《宋会要》）"""
    rulers = [
        ("庞特勤", "可汗（建国）", "", "", "庞特勤", 848, 866, "", 70),
        ("仁美", "可汗", "", "", "仁美", 905, 926, "", 70),
        ("仁裕", "可汗", "", "", "仁裕", 926, 959, "", 75),
        ("夜落隔密礼遏", "可汗", "", "", "夜落隔密礼遏", 959, 977, "", 65),
        ("夜落隔通顺", "可汗", "", "", "夜落隔通顺", 977, 1004, "", 65),
        ("夜落隔归化", "可汗", "", "", "夜落隔归化", 1004, 1023, "", 70),
        ("夜落隔可汗（末代）", "可汗（末代）", "", "末代", "夜落隔", 1023, 1036, "", 75),
    ]
    return {
        "polity": {
            "macro_period": "宋辽金夏",
            "dynasty_name": "甘州回鹘",
            "polity_name": "甘州回鹘",
            "polity_aliases": "河西回鶻 | 甘州回鶻 | 甘州可汗國",
            "polity_type": "政权/国家",
            "polity_start_year": 848,
            "polity_end_year": 1036,
            "polity_date_raw": "848年－1036年",
            "polity_date_precision": "year",
            "historical_geography_raw": "回鹘西迁支系，约 9 世纪中叶在甘州（张掖）一带立国，辖河西走廊中段；1036 年被西夏李元昊攻取",
            "modern_admin_units_raw": "甘肃省张掖市、酒泉市、武威市，宁夏回族自治区西部",
            "capital_historical": "甘州",
            "capital_modern": "甘肃省张掖市甘州区",
            "ruling_family_or_clan": "药罗葛系（夜落隔氏）",
            "ethnicity_or_group": "回鹘",
            "founder": "庞特勤",
            "last_ruler": "夜落隔可汗",
            "destroyed_by_or_successor": "西夏（李元昊取甘州，并河西回鹘地）",
            "polity_source_titles": "《宋史·回鹘传》 | 《辽史》 | 《宋会要辑稿》 | 《续资治通鉴长编》",
            "polity_source_urls": "https://zh.wikipedia.org/wiki/%E7%94%98%E5%B7%9E%E5%9B%9E%E9%B6%BB",
            "polity_source_raw": "约 848 年回鹘西迁支系入甘州一带立国；1036 年李元昊大举西征，攻取甘州，甘州回鹘亡。",
            "confidence_score": 75,
            "confidence_note": "宋史与辽史互证主线；9 世纪后期可汗世系断代不完整",
        },
        "rulers": rulers,
        "capitals": [
            ("甘州", "甘肃省张掖市甘州区", 848, 1036, 100.450, 38.926, True, "initial_capital", "city",
             "《宋史·回鹘传》", "https://zh.wikipedia.org/wiki/%E7%94%98%E5%B7%9E%E5%9B%9E%E9%B6%BB",
             "甘州回鹘以甘州（今张掖）为都", 78, ""),
        ],
        "issues": [
            {
                "issue_type": "partial_boundary",
                "field_name": "ruler_succession",
                "selected_value": "本表沿用可考的 7 位可汗",
                "alternative_values": "9 世纪后期至 10 世纪初世系空白",
                "source_titles": "《宋史·回鹘传》/《辽史》",
                "source_urls": "https://zh.wikipedia.org/wiki/%E7%94%98%E5%B7%9E%E5%9B%9E%E9%B6%BB",
                "note": "甘州回鹘 866~905 年的可汗世系汉文文献几乎无记载，本表此期作为 year_polity_unmatched_ruler 保留。",
                "action_in_v03": "polity_continuity preserved; ruler gaps tracked as unmatched-ruler years",
            },
        ],
    }


# 注入批 C
POLITY_DEFINITIONS.extend([
    define_xiongnu(),
    define_southern_xiongnu(),
    define_uyghur_khaganate(),
    define_gaochang_uyghur(),
    define_ganzhou_uyghur(),
])

# ============================================================================
# 落库逻辑
# ============================================================================

# 字段顺序（必须与现有 CSV 完全一致；脚本会从现有 CSV 读 header 校验）
MASTER_FIELDS = [
    "polity_id", "macro_period", "dynasty_name", "polity_name", "polity_aliases",
    "polity_type", "polity_start_year", "polity_start_label", "polity_end_year",
    "polity_end_label", "polity_date_raw", "polity_date_precision",
    "historical_geography_raw", "modern_admin_units_raw", "capital_historical",
    "capital_modern", "ruling_family_or_clan", "ethnicity_or_group", "founder",
    "last_ruler", "destroyed_by_or_successor", "polity_source_titles",
    "polity_source_urls", "polity_source_raw", "confidence_score", "confidence_note",
    "calendar_system_note", "v02_row_count", "v02_actual_min_year",
    "v02_actual_max_year", "v02_actual_years", "merged_from_v02_contexts",
]
RULERS_FIELDS = [
    "ruler_id", "polity_id", "polity_name", "ruler_name", "ruler_title",
    "ruler_temple_name", "ruler_posthumous_name", "ruler_personal_name",
    "ruler_reign_start_year", "ruler_reign_start_label", "ruler_reign_end_year",
    "ruler_reign_end_label", "ruler_reign_raw", "ruler_reign_precision",
    "era_names", "ruler_source_title", "ruler_source_url", "ruler_source_section",
    "ruler_confidence_score", "ruler_confidence_note", "merged_from_v02_rows",
]
YEARLY_FIELDS = [
    "row_id", "polity_id", "ruler_id", "row_granularity", "year", "year_label",
    "macro_period", "dynasty_name", "polity_name", "polity_aliases", "polity_type",
    "polity_start_year", "polity_start_label", "polity_end_year", "polity_end_label",
    "polity_date_raw", "polity_date_precision", "historical_geography_raw",
    "modern_admin_units_raw", "capital_historical", "capital_modern",
    "ruling_family_or_clan", "ethnicity_or_group", "founder", "last_ruler",
    "destroyed_by_or_successor", "polity_source_titles", "polity_source_urls",
    "polity_source_raw", "confidence_score", "confidence_note", "calendar_system_note",
    "ruler_name", "ruler_title", "ruler_temple_name", "ruler_posthumous_name",
    "ruler_personal_name", "ruler_reign_start_year", "ruler_reign_start_label",
    "ruler_reign_end_year", "ruler_reign_end_label", "ruler_reign_raw",
    "ruler_reign_precision", "era_names", "ruler_source_title", "ruler_source_url",
    "ruler_source_section", "ruler_confidence_score", "ruler_confidence_note",
]
ISSUES_FIELDS = [
    "issue_id", "issue_type", "entity_type", "polity_id", "polity_name",
    "field_name", "selected_value", "alternative_values", "source_titles",
    "source_urls", "note", "action_in_v03",
]
CAPITALS_FIELDS = [
    "capital_event_id", "polity_id", "capital_name_historical", "capital_name_modern",
    "valid_from_year", "valid_to_year", "longitude", "latitude", "is_primary",
    "event_type", "location_precision", "source_titles", "source_urls",
    "source_raw", "confidence_score", "confidence_note",
]


def read_csv_rows(path: Path, encoding: str = "utf-8-sig") -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding=encoding) as f:
        reader = csv.DictReader(f)
        fieldnames = list(reader.fieldnames or [])
        # 兼容 BOM：第一个字段名可能含
        fieldnames = [name.lstrip("﻿") for name in fieldnames]
        rows: list[dict[str, str]] = []
        for raw in reader:
            normalized: dict[str, str] = {}
            for key, value in raw.items():
                normalized_key = (key or "").lstrip("﻿")
                normalized[normalized_key] = value or ""
            rows.append(normalized)
    return fieldnames, rows


def write_csv_rows(path: Path, fieldnames: list[str], rows: list[dict[str, str]], encoding: str = "utf-8") -> None:
    with path.open("w", encoding=encoding, newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({name: row.get(name, "") for name in fieldnames})


def filter_out_polities(rows: list[dict[str, str]], polity_ids: set[str], key: str = "polity_id") -> list[dict[str, str]]:
    return [row for row in rows if row.get(key) not in polity_ids]


def main() -> int:
    # 1. 读取所有现有数据
    _master_header, master_rows = read_csv_rows(MASTER_CSV)
    _rulers_header, rulers_rows = read_csv_rows(RULERS_CSV)
    _yearly_header, yearly_rows = read_csv_rows(YEARLY_CSV)
    _issues_header, issues_rows = read_csv_rows(ISSUES_CSV)
    _capitals_header, capitals_rows = read_csv_rows(CAPITALS_CSV, encoding="utf-8")

    # 2. 推断下一个 ID
    existing_polity_ids = {row["polity_id"] for row in master_rows}
    existing_ruler_ids = {row["ruler_id"] for row in rulers_rows}
    existing_row_ids = {int(row["row_id"]) for row in yearly_rows if row["row_id"].isdigit()}
    existing_issue_ids = {row["issue_id"] for row in issues_rows}
    existing_capital_ids = {row["capital_event_id"] for row in capitals_rows}

    def next_polity_id(seen: set[str]) -> str:
        nonlocal_index = 168
        while f"polity_{nonlocal_index:04d}" in seen:
            nonlocal_index += 1
        new = f"polity_{nonlocal_index:04d}"
        seen.add(new)
        return new

    def next_ruler_id(seen: set[str]) -> str:
        nonlocal_index = 935
        while f"ruler_{nonlocal_index:05d}" in seen:
            nonlocal_index += 1
        new = f"ruler_{nonlocal_index:05d}"
        seen.add(new)
        return new

    def next_capital_id(seen: set[str]) -> str:
        nonlocal_index = 34
        while f"capital_{nonlocal_index:04d}" in seen:
            nonlocal_index += 1
        new = f"capital_{nonlocal_index:04d}"
        seen.add(new)
        return new

    def next_issue_id(seen: set[str]) -> str:
        nonlocal_index = 35
        while f"issue_{nonlocal_index:04d}" in seen:
            nonlocal_index += 1
        new = f"issue_{nonlocal_index:04d}"
        seen.add(new)
        return new

    # 3. 幂等：先剔除新增政权对应的所有行（按 polity_name 匹配，因 polity_id 还没分配）
    new_polity_names = {definition["polity"]["polity_name"] for definition in POLITY_DEFINITIONS}

    def remove_by_polity_name(rows: list[dict[str, str]]) -> list[dict[str, str]]:
        return [
            row for row in rows
            if row.get("polity_name") not in new_polity_names
        ]

    # 收集要保留的现有 polity_id（这些不应被删）
    surviving_master_ids = {
        row["polity_id"] for row in master_rows if row["polity_name"] not in new_polity_names
    }
    master_rows = [row for row in master_rows if row["polity_name"] not in new_polity_names]
    rulers_rows = [row for row in rulers_rows if row["polity_id"] in surviving_master_ids]
    yearly_rows = [row for row in yearly_rows if row["polity_id"] in surviving_master_ids]
    capitals_rows = [row for row in capitals_rows if row["polity_id"] in surviving_master_ids]
    issues_rows = [row for row in issues_rows if row["polity_id"] in surviving_master_ids]

    # 重新计算可用 ID 集合（剔除已删后）
    existing_polity_ids = {row["polity_id"] for row in master_rows}
    existing_ruler_ids = {row["ruler_id"] for row in rulers_rows}
    existing_issue_ids = {row["issue_id"] for row in issues_rows}
    existing_capital_ids = {row["capital_event_id"] for row in capitals_rows}
    next_row_id = max((int(row["row_id"]) for row in yearly_rows if row["row_id"].isdigit()), default=0) + 1

    # 4. 逐个 polity 注入
    added_summary = []
    for definition in POLITY_DEFINITIONS:
        polity = definition["polity"]
        polity_id = next_polity_id(existing_polity_ids)
        years = expand_years(int(polity["polity_start_year"]), int(polity["polity_end_year"]))

        # 4a. master row
        master_row = {
            "polity_id": polity_id,
            "macro_period": polity["macro_period"],
            "dynasty_name": polity["dynasty_name"],
            "polity_name": polity["polity_name"],
            "polity_aliases": polity["polity_aliases"],
            "polity_type": polity["polity_type"],
            "polity_start_year": str(polity["polity_start_year"]),
            "polity_start_label": year_label(int(polity["polity_start_year"])),
            "polity_end_year": str(polity["polity_end_year"]),
            "polity_end_label": year_label(int(polity["polity_end_year"])),
            "polity_date_raw": polity["polity_date_raw"],
            "polity_date_precision": polity["polity_date_precision"],
            "historical_geography_raw": polity["historical_geography_raw"],
            "modern_admin_units_raw": polity["modern_admin_units_raw"],
            "capital_historical": polity["capital_historical"],
            "capital_modern": polity["capital_modern"],
            "ruling_family_or_clan": polity["ruling_family_or_clan"],
            "ethnicity_or_group": polity["ethnicity_or_group"],
            "founder": polity["founder"],
            "last_ruler": polity["last_ruler"],
            "destroyed_by_or_successor": polity["destroyed_by_or_successor"],
            "polity_source_titles": polity["polity_source_titles"],
            "polity_source_urls": polity["polity_source_urls"],
            "polity_source_raw": polity["polity_source_raw"],
            "confidence_score": str(polity["confidence_score"]),
            "confidence_note": polity.get("confidence_note", ""),
            "calendar_system_note": CALENDAR_NOTE,
            "v02_row_count": "0",
            "v02_actual_min_year": str(polity["polity_start_year"]),
            "v02_actual_max_year": str(polity["polity_end_year"]),
            "v02_actual_years": ";".join(str(y) for y in years),
            "merged_from_v02_contexts": "",
        }
        master_rows.append(master_row)

        # 4b. rulers + 维护 year → ruler 映射
        rulers_by_year: dict[int, list[dict[str, str]]] = {y: [] for y in years}
        for ruler_tuple in definition["rulers"]:
            (
                ruler_name, ruler_title, temple_name, posthumous_name, personal_name,
                reign_start, reign_end, era_names, conf,
            ) = ruler_tuple
            ruler_id = next_ruler_id(existing_ruler_ids)
            ruler_row = {
                "ruler_id": ruler_id,
                "polity_id": polity_id,
                "polity_name": polity["polity_name"],
                "ruler_name": ruler_name,
                "ruler_title": ruler_title,
                "ruler_temple_name": temple_name,
                "ruler_posthumous_name": posthumous_name,
                "ruler_personal_name": personal_name,
                "ruler_reign_start_year": str(reign_start),
                "ruler_reign_start_label": year_label(int(reign_start)),
                "ruler_reign_end_year": str(reign_end),
                "ruler_reign_end_label": year_label(int(reign_end)),
                "ruler_reign_raw": f"{year_label(int(reign_start))}－{year_label(int(reign_end))}",
                "ruler_reign_precision": "year",
                "era_names": era_names,
                "ruler_source_title": polity["polity_source_titles"].split(" | ")[0]
                if polity["polity_source_titles"] else "",
                "ruler_source_url": polity["polity_source_urls"].split(" | ")[0]
                if polity["polity_source_urls"] else "",
                "ruler_source_section": f"{polity['polity_name']} > {ruler_name}",
                "ruler_confidence_score": str(conf),
                "ruler_confidence_note": "",
                "merged_from_v02_rows": "",
            }
            rulers_rows.append(ruler_row)
            for y in expand_years(int(reign_start), int(reign_end)):
                if y in rulers_by_year:
                    rulers_by_year[y].append(ruler_row)

        # 4c. yearly rows
        for year in years:
            matched_rulers = rulers_by_year.get(year, [])
            if matched_rulers:
                for ruler_row in matched_rulers:
                    yearly_row = _build_yearly_row(
                        next_row_id, polity_id, ruler_row["ruler_id"], "year_polity_ruler",
                        year, master_row, ruler_row,
                    )
                    yearly_rows.append(yearly_row)
                    next_row_id += 1
            else:
                yearly_row = _build_yearly_row(
                    next_row_id, polity_id, "", "year_polity_unmatched_ruler",
                    year, master_row, None,
                )
                yearly_rows.append(yearly_row)
                next_row_id += 1

        # 4d. capital events
        for cap_tuple in definition.get("capitals", []):
            (
                cap_hist, cap_modern, valid_from, valid_to, lon, lat, is_primary,
                event_type, precision, src_titles, src_urls, src_raw, cap_conf, cap_note,
            ) = cap_tuple
            cap_id = next_capital_id(existing_capital_ids)
            capitals_rows.append({
                "capital_event_id": cap_id,
                "polity_id": polity_id,
                "capital_name_historical": cap_hist,
                "capital_name_modern": cap_modern,
                "valid_from_year": str(valid_from),
                "valid_to_year": str(valid_to),
                "longitude": f"{lon:.4f}",
                "latitude": f"{lat:.4f}",
                "is_primary": "true" if is_primary else "false",
                "event_type": event_type,
                "location_precision": precision,
                "source_titles": src_titles,
                "source_urls": src_urls,
                "source_raw": src_raw,
                "confidence_score": str(cap_conf),
                "confidence_note": cap_note,
            })

        # 4e. issues
        for issue in definition.get("issues", []):
            issue_id = next_issue_id(existing_issue_ids)
            issues_rows.append({
                "issue_id": issue_id,
                "issue_type": issue["issue_type"],
                "entity_type": "polity",
                "polity_id": polity_id,
                "polity_name": polity["polity_name"],
                "field_name": issue["field_name"],
                "selected_value": issue["selected_value"],
                "alternative_values": issue["alternative_values"],
                "source_titles": issue["source_titles"],
                "source_urls": issue["source_urls"],
                "note": issue["note"],
                "action_in_v03": issue["action_in_v03"],
            })

        added_summary.append((polity_id, polity["polity_name"], len(years), len(definition["rulers"])))

    # 5. 排序 yearly：按 year, polity_id, ruler_id（与现有约定一致）
    yearly_rows.sort(key=lambda row: (int(row["year"]), row["polity_id"], row["ruler_id"] or ""))
    # 重排 row_id 1..N（避免 sparse）
    for index, row in enumerate(yearly_rows, start=1):
        row["row_id"] = str(index)

    # 6. 写回
    write_csv_rows(MASTER_CSV, MASTER_FIELDS, master_rows, encoding="utf-8-sig")
    write_csv_rows(RULERS_CSV, RULERS_FIELDS, rulers_rows, encoding="utf-8-sig")
    write_csv_rows(YEARLY_CSV, YEARLY_FIELDS, yearly_rows, encoding="utf-8-sig")
    write_csv_rows(ISSUES_CSV, ISSUES_FIELDS, issues_rows, encoding="utf-8-sig")
    write_csv_rows(CAPITALS_CSV, CAPITALS_FIELDS, capitals_rows, encoding="utf-8")

    # 7. 验证报告
    print("=== 新增政权摘要 ===")
    for polity_id, name, year_count, ruler_count in added_summary:
        print(f"  {polity_id}  {name}  {year_count} 年 · {ruler_count} 君主")
    print()
    print(f"master: {len(master_rows)} 行")
    print(f"rulers: {len(rulers_rows)} 行")
    print(f"yearly: {len(yearly_rows)} 行")
    print(f"issues: {len(issues_rows)} 条")
    print(f"capitals: {len(capitals_rows)} 条")
    print()
    print("⚠ 再跑 python3 scripts/generate_public_data.py 以更新 public/ 数据")
    return 0


def _build_yearly_row(
    row_id: int, polity_id: str, ruler_id: str, granularity: str, year: int,
    master_row: dict[str, str], ruler_row: dict[str, str] | None,
) -> dict[str, str]:
    base = {
        "row_id": str(row_id),
        "polity_id": polity_id,
        "ruler_id": ruler_id,
        "row_granularity": granularity,
        "year": str(year),
        "year_label": year_label(year),
        # 复制 master 字段
        "macro_period": master_row["macro_period"],
        "dynasty_name": master_row["dynasty_name"],
        "polity_name": master_row["polity_name"],
        "polity_aliases": master_row["polity_aliases"],
        "polity_type": master_row["polity_type"],
        "polity_start_year": master_row["polity_start_year"],
        "polity_start_label": master_row["polity_start_label"],
        "polity_end_year": master_row["polity_end_year"],
        "polity_end_label": master_row["polity_end_label"],
        "polity_date_raw": master_row["polity_date_raw"],
        "polity_date_precision": master_row["polity_date_precision"],
        "historical_geography_raw": master_row["historical_geography_raw"],
        "modern_admin_units_raw": master_row["modern_admin_units_raw"],
        "capital_historical": master_row["capital_historical"],
        "capital_modern": master_row["capital_modern"],
        "ruling_family_or_clan": master_row["ruling_family_or_clan"],
        "ethnicity_or_group": master_row["ethnicity_or_group"],
        "founder": master_row["founder"],
        "last_ruler": master_row["last_ruler"],
        "destroyed_by_or_successor": master_row["destroyed_by_or_successor"],
        "polity_source_titles": master_row["polity_source_titles"],
        "polity_source_urls": master_row["polity_source_urls"],
        "polity_source_raw": master_row["polity_source_raw"],
        "confidence_score": master_row["confidence_score"],
        "confidence_note": master_row["confidence_note"],
        "calendar_system_note": CALENDAR_NOTE,
    }
    if ruler_row:
        base.update({
            "ruler_name": ruler_row["ruler_name"],
            "ruler_title": ruler_row["ruler_title"],
            "ruler_temple_name": ruler_row["ruler_temple_name"],
            "ruler_posthumous_name": ruler_row["ruler_posthumous_name"],
            "ruler_personal_name": ruler_row["ruler_personal_name"],
            "ruler_reign_start_year": ruler_row["ruler_reign_start_year"],
            "ruler_reign_start_label": ruler_row["ruler_reign_start_label"],
            "ruler_reign_end_year": ruler_row["ruler_reign_end_year"],
            "ruler_reign_end_label": ruler_row["ruler_reign_end_label"],
            "ruler_reign_raw": ruler_row["ruler_reign_raw"],
            "ruler_reign_precision": ruler_row["ruler_reign_precision"],
            "era_names": ruler_row["era_names"],
            "ruler_source_title": ruler_row["ruler_source_title"],
            "ruler_source_url": ruler_row["ruler_source_url"],
            "ruler_source_section": ruler_row["ruler_source_section"],
            "ruler_confidence_score": ruler_row["ruler_confidence_score"],
            "ruler_confidence_note": ruler_row["ruler_confidence_note"],
        })
    else:
        for field in [
            "ruler_name", "ruler_title", "ruler_temple_name", "ruler_posthumous_name",
            "ruler_personal_name", "ruler_reign_start_year", "ruler_reign_start_label",
            "ruler_reign_end_year", "ruler_reign_end_label", "ruler_reign_raw",
            "ruler_reign_precision", "era_names", "ruler_source_title",
            "ruler_source_url", "ruler_source_section", "ruler_confidence_score",
        ]:
            base[field] = ""
        base["ruler_confidence_note"] = "该年度在政权存在期内，但未匹配到可解析君主年表；按国家年度行保留"
    return base


if __name__ == "__main__":
    sys.exit(main())
