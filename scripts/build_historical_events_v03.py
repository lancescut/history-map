#!/usr/bin/env python3
"""Build the v03 displayable historical event library.

This layer is intentionally strict about what counts as an event:

- existing hand-written key events remain core/representative records;
- polity start/end years become concise establishment/extinction events;
- routine yearly status, ruler, capital, and geography facts stay out of the
  event stream;
- years without exact events receive verified range anchors that explain the
  historical process in force without pretending a sudden event happened.
"""

from __future__ import annotations

import csv
import hashlib
from collections import defaultdict
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
INPUT_DIR = ROOT / "input" / "v03"
EVENTS_CSV = INPUT_DIR / "historical_events_v03.csv"
YEARLY_CSV = INPUT_DIR / "chinese_history_polities_yearly_v03.csv"
MASTER_CSV = INPUT_DIR / "chinese_history_polities_master_v03.csv"
CAPITALS_CSV = INPUT_DIR / "capital_events_v03.csv"
EVENT_REVIEW_REPORT = INPUT_DIR / "historical_events_v03_review_report.csv"
EVENT_COVERAGE_REPORT = INPUT_DIR / "historical_event_coverage_report_v03.csv"

YEAR_MIN = -1046
YEAR_MAX = 1949

FIELDNAMES = [
    "event_id",
    "year",
    "sort_order",
    "date_label",
    "date_precision",
    "coverage_role",
    "coverage_start_year",
    "coverage_end_year",
    "coverage_group_id",
    "item_kind",
    "event_type",
    "title",
    "description",
    "significance",
    "primary_education_stage",
    "education_stage_tags",
    "curriculum_basis",
    "importance_level",
    "display_priority",
    "related_polity_ids",
    "related_people",
    "location_name",
    "longitude",
    "latitude",
    "location_historical_name",
    "location_modern_name",
    "location_modern_admin_id",
    "location_precision",
    "location_confidence_score",
    "location_source_titles",
    "location_source_urls",
    "location_note",
    "source_titles",
    "source_urls",
    "source_type",
    "confidence_score",
    "confidence_note",
    "fact_review_status",
    "review_note",
]

ITEM_KINDS = {"core_event", "representative_event", "annual_fact", "context", "annual_chronicle", "range_anchor"}
COVERAGE_ROLES = {"exact_year_event", "annual_chronicle", "range_anchor", "nearby_enrichment"}
DATE_PRECISIONS = {"year", "approx", "range"}
EDUCATION_STAGES = {"小学", "初中", "高中", "大学"}
LOCATION_PRECISIONS = {"exact", "city", "region", "approximate"}
REVIEW_STATUSES = {"verified", "candidate", "needs_review", "rejected"}
GENERATED_PREFIXES = ("annual_", "context_", "generated_", "supp_", "range_")
DISALLOWED_EVENT_TYPES = {
    "polity_status",
    "period_context",
    "ruler_reign",
    "capital_status",
    "territory_context",
    "ruling_group",
    "source_context",
}
DISALLOWED_TEXT_FRAGMENTS = (
    "持续存在",
    "年度政权格局",
    "当前有效主都城",
    "匹配到在位君主",
    "v03 记录",
)
LEGACY_POLITY_ID_MAP = {
    # historical_events_v03.csv seed data briefly used this ad hoc id before
    # 后金 was normalized into the v03 polity master table.
    "polity_0048_后金": "polity_0054",
}

COURSE_SOURCE_TITLES = "《义务教育历史课程标准（2022年版）》|《普通高中历史课程标准（2017年版2020年修订）》"
COURSE_SOURCE_URLS = (
    "https://www.htu.edu.cn/history/2022/0905/c18511a251113/page.htm|"
    "https://www.pep.com.cn/xw/zt/rjwy/gzkb2020/202205/P020220517518171679768.pdf"
)
TIMELINE_SOURCE_TITLE = "中国社会科学出版社《中国历史年表数据库》"
TIMELINE_SOURCE_URL = "https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"
LOCATION_SOURCE_TITLES = "CHGIS中国历史地理信息系统|《中国历史地图集》"
LOCATION_SOURCE_URLS = "https://chgis.fas.harvard.edu/pages/intro/|https://east.library.utoronto.ca/internet-resource/chinese-civilization-time-and-space"
CTEXT_SOURCE_TITLE = "中国哲学书电子化计划（Chinese Text Project）"
CTEXT_SOURCE_URL = "https://ctext.org/"

MAJOR_POLITY_NAMES = {
    "西周", "东周", "秦朝", "西汉", "新朝", "东汉", "曹魏", "蜀汉", "东吴",
    "西晋", "东晋", "北魏", "隋朝", "唐朝", "后梁", "后唐", "后晋", "后汉",
    "后周", "北宋", "南宋", "辽朝", "金朝", "西夏", "元朝", "明朝", "清朝",
    "后金", "明郑", "太平天国",
}

SCHOOL_EVENT_KEYWORDS = (
    "武王克商", "西周", "东周", "春秋", "战国", "秦", "汉", "三国", "晋",
    "南北朝", "隋", "唐", "宋", "辽", "金", "元", "明", "清", "鸦片",
    "太平天国", "洋务", "甲午", "戊戌", "义和团", "辛亥",
)

DISPLAY_TEXT_REPLACEMENTS = {
    "國": "国",
    "與": "与",
    "後": "后",
    "於": "于",
    "臺": "台",
    "對": "对",
    "劉": "刘",
    "趙": "赵",
    "淵": "渊",
    "貼": "帖",
    "爾": "尔",
    "懽": "欢",
    "構": "构",
    "齊": "齐",
    "樂": "乐",
    "陽": "阳",
    "孫": "孙",
    "權": "权",
    "司馬": "司马",
    "蕭": "萧",
    "陳": "陈",
    "楊": "杨",
    "錢": "钱",
    "馬": "马",
    "興": "兴",
    "遠": "远",
    "極": "极",
    "溫": "温",
    "開": "开",
    "寧": "宁",
    "長": "长",
    "涼": "凉",
    "靜": "静",
    "見": "见",
    "寶": "宝",
    "覺": "觉",
    "閔": "闵",
    "莊": "庄",
    "勗": "勖",
    "業": "业",
    "鄴": "邺",
    "龍": "龙",
    "統": "统",
    "萬": "万",
    "廣": "广",
    "漢": "汉",
    "遼": "辽",
    "吳": "吴",
    "晉": "晋",
    "閩": "闽",
}

PERSON_DISPLAY_OVERRIDES = {
    "始皇帝 政": "秦王政",
    "武帝 司馬炎": "司马炎",
    "道武帝 拓跋珪": "拓跋珪",
    "武帝 刘裕": "刘裕",
    "高帝 蕭道成": "萧道成",
    "武帝 蕭衍": "萧衍",
    "武帝 陳霸先": "陈霸先",
    "孝閔帝 宇文覺": "宇文觉",
    "太祖 朱溫": "朱温",
    "莊宗 李存勗": "李存勖",
    "高祖 石敬瑭": "石敬瑭",
    "高祖 刘知遠": "刘知远",
    "太祖 郭威": "郭威",
    "高宗 赵构": "赵构",
    "顺帝 妥欢帖睦尔": "妥欢帖睦尔",
    "太宗 皇太極": "皇太极",
}

SEED_DESCRIPTION_OVERRIDES = {
    "event_0001": "前1046年，周武王姬发在牧野击败商纣，西周建立。",
    "event_0002": "前771年，犬戎攻破镐京，周幽王被杀，西周灭亡。",
    "event_0003": "前770年，周平王迁都洛邑，东周开始。",
    "event_0004": "前403年，周威烈王承认韩、赵、魏为诸侯，三家分晋成为战国开端。",
    "event_0005": "前256年，秦灭东周残余王室，周王朝结束。",
    "event_0006": "前230年，秦军攻下新郑，韩国灭亡。",
    "event_0007": "前225年，王贲攻破大梁，魏国灭亡。",
    "event_0008": "前223年，王翦率秦军灭楚，楚地归秦。",
    "event_0009": "前221年，秦灭齐，六国全部并入秦。",
    "event_0010": "前209年，陈胜、吴广在大泽乡起兵，反秦战争爆发。",
    "event_0011": "前206年，刘邦入关，子婴投降，秦朝灭亡。",
    "event_0012": "前202年，刘邦击败项羽后称帝，西汉建立。",
    "event_0013": "前133年，汉武帝在马邑设伏匈奴未成，汉匈战争转入正面冲突。",
    "event_0014": "前121年，霍去病两次出击河西，重创匈奴。",
    "event_0015": "前119年，卫青、霍去病远征漠北，匈奴主力北退。",
    "event_0016": "前60年，西汉设置西域都护，管理天山南北各地。",
    "event_0017": "9年，王莽代汉称帝，新朝建立。",
    "event_0018": "25年，刘秀称帝，东汉建立。",
    "event_0019": "184年，张角发动黄巾起义，东汉统治迅速动摇。",
    "event_0020": "208年，孙刘联军在赤壁击败曹操，三国格局成形。",
    "event_0021": "220年，曹丕接受汉献帝禅让称帝，曹魏建立。",
    "event_0022": "280年，晋军灭吴，三国归于西晋。",
    "event_0023": "311年，匈奴汉国攻破洛阳，晋怀帝被俘，永嘉之乱爆发。",
    "event_0024": "317年，司马睿在建康称帝，东晋建立。",
    "event_0025": "383年，谢玄率东晋军在淝水击败前秦苻坚。",
    "event_0026": "439年，北魏灭北凉，统一中国北方。",
    "event_0027": "581年，杨坚受禅称帝，隋朝建立。",
    "event_0028": "589年，隋军南下灭陈，南北重新统一。",
    "event_0029": "618年，李渊在长安称帝，唐朝建立。",
    "event_0030": "626年，李世民发动玄武门之变，随后即位为唐太宗。",
    "event_0031": "755年，安禄山起兵反唐，安史之乱爆发。",
    "event_0032": "907年，朱温代唐称帝，唐朝灭亡，五代开始。",
    "event_0033": "960年，赵匡胤发动陈桥兵变，北宋建立。",
    "event_0034": "979年，宋太宗灭北汉，五代十国分裂局面结束。",
    "event_0035": "1004年，宋辽订立澶渊之盟，双方进入长期对峙与互市。",
    "event_0036": "1115年，完颜阿骨打称帝建金，女真政权崛起。",
    "event_0037": "1127年，金军攻破东京，徽钦二帝被俘，北宋灭亡。",
    "event_0038": "1234年，蒙古与南宋联军灭金。",
    "event_0039": "1271年，忽必烈定国号为大元，元朝建立。",
    "event_0040": "1279年，崖山海战后南宋灭亡，元朝完成统一。",
    "event_0041": "1368年，朱元璋称帝建立明朝，明军随后攻入大都。",
    "event_0042": "1449年，明英宗北征瓦剌兵败被俘，土木之变爆发。",
    "event_0043": "1616年，努尔哈赤称汗，后金建立。",
    "event_0044": "1636年，皇太极在沈阳改国号为清。",
    "event_0045": "1644年，李自成攻入北京，崇祯自缢，明朝灭亡。",
    "event_0046": "1683年，施琅攻取台湾，郑克塽投降，明郑结束。",
    "event_0047": "1759年，清军平定大小和卓叛乱，新疆重新纳入清朝统治。",
    "event_0048": "1840年，英军舰队进犯广东，第一次鸦片战争爆发。",
    "event_0049": "1851年，洪秀全在金田起义，太平天国运动开始。",
    "event_0050": "1900年，八国联军侵华，清廷逃离北京。",
    "event_0051": "1911年，武昌起义爆发，各省相继宣布独立。",
    "event_0052": "1912年，宣统帝发布退位诏书，清朝灭亡。",
}

SEED_POLITY_ID_OVERRIDES = {
    "event_0001": ["polity_0129"],
    "event_0002": ["polity_0129"],
    "event_0003": ["polity_0003"],
    "event_0004": ["polity_0073", "polity_0161", "polity_0144", "polity_0165"],
    "event_0005": ["polity_0003", "polity_0130", "polity_0004"],
    "event_0006": ["polity_0161"],
    "event_0007": ["polity_0165"],
    "event_0008": ["polity_0084"],
    "event_0009": ["polity_0109", "polity_0110", "polity_0167"],
    "event_0010": ["polity_0110"],
    "event_0011": ["polity_0110"],
    "event_0012": ["polity_0134"],
    "event_0013": ["polity_0134", "polity_0178"],
    "event_0014": ["polity_0134", "polity_0178"],
    "event_0015": ["polity_0134", "polity_0178"],
    "event_0016": ["polity_0134"],
    "event_0017": ["polity_0071"],
    "event_0018": ["polity_0006"],
    "event_0019": ["polity_0006"],
    "event_0020": ["polity_0006"],
    "event_0021": ["polity_0006", "polity_0075"],
    "event_0022": ["polity_0132", "polity_0002"],
    "event_0023": ["polity_0132", "polity_0093"],
    "event_0024": ["polity_0005"],
    "event_0025": ["polity_0005", "polity_0021"],
    "event_0026": ["polity_0030", "polity_0024"],
    "event_0027": ["polity_0158", "polity_0025"],
    "event_0028": ["polity_0158", "polity_0157"],
    "event_0029": ["polity_0158", "polity_0059"],
    "event_0030": ["polity_0059"],
    "event_0031": ["polity_0059"],
    "event_0032": ["polity_0059", "polity_0048"],
    "event_0033": ["polity_0026"],
    "event_0034": ["polity_0026", "polity_0027"],
    "event_0035": ["polity_0026", "polity_0146"],
    "event_0036": ["polity_0154"],
    "event_0037": ["polity_0026", "polity_0034", "polity_0154"],
    "event_0038": ["polity_0154", "polity_0034"],
    "event_0039": ["polity_0013"],
    "event_0040": ["polity_0034", "polity_0013"],
    "event_0041": ["polity_0072", "polity_0013"],
    "event_0042": ["polity_0072"],
    "event_0043": ["polity_0054"],
    "event_0044": ["polity_0054", "polity_0096"],
    "event_0045": ["polity_0072", "polity_0096"],
    "event_0046": ["polity_0096"],
    "event_0047": ["polity_0096"],
    "event_0048": ["polity_0096"],
    "event_0049": ["polity_0096"],
    "event_0050": ["polity_0096"],
    "event_0051": ["polity_0096"],
    "event_0052": ["polity_0096"],
}


def loc(
    historical_name: str,
    modern_name: str,
    longitude: float,
    latitude: float,
    *,
    admin_id: str = "",
    precision: str = "city",
    confidence: int = 82,
    note: str = "",
    aliases: tuple[str, ...] = (),
) -> dict[str, Any]:
    return {
        "location_name": modern_name,
        "location_historical_name": historical_name,
        "location_modern_name": modern_name,
        "location_modern_admin_id": admin_id,
        "longitude": f"{longitude:.4f}",
        "latitude": f"{latitude:.4f}",
        "location_precision": precision,
        "location_confidence_score": str(confidence),
        "location_source_titles": LOCATION_SOURCE_TITLES,
        "location_source_urls": LOCATION_SOURCE_URLS,
        "location_note": note,
        "aliases": aliases,
    }


LOCATION_GAZETTEER: dict[str, dict[str, Any]] = {
    "muye": loc("牧野", "河南省新乡市淇县一带", 114.4737, 35.3989, admin_id="CN-HA", precision="region", confidence=83, aliases=("牧野", "淇县", "新乡")),
    "haojing": loc("镐京", "陕西省西安市长安区斗门一带", 108.7500, 34.2200, admin_id="CN-SN", precision="region", confidence=84, aliases=("镐京", "宗周", "斗门", "西安")),
    "luoyi": loc("雒邑", "河南省洛阳市", 112.4540, 34.6197, admin_id="CN-HA", precision="city", confidence=88, aliases=("雒邑", "洛邑", "成周", "洛阳")),
    "luoyang": loc("洛阳", "河南省洛阳市", 112.4540, 34.6197, admin_id="CN-HA", precision="city", confidence=90, aliases=("洛陽", "洛阳")),
    "xianyang": loc("咸阳", "陕西省咸阳市", 108.7088, 34.3299, admin_id="CN-SN", precision="city", confidence=90, aliases=("咸阳", "咸陽")),
    "changan": loc("长安", "陕西省西安市", 108.9398, 34.3416, admin_id="CN-SN", precision="city", confidence=90, aliases=("长安", "長安", "大兴", "大興", "西安")),
    "liyang": loc("栎阳", "陕西省西安市阎良区", 109.2300, 34.6600, admin_id="CN-SN", precision="region", confidence=78, aliases=("栎阳", "櫟陽", "阎良")),
    "xinzheng": loc("新郑", "河南省新郑市", 113.7400, 34.4000, admin_id="CN-HA", precision="city", confidence=83, aliases=("新郑", "新鄭")),
    "daliang": loc("大梁", "河南省开封市", 114.3076, 34.7973, admin_id="CN-HA", precision="city", confidence=86, aliases=("大梁", "汴梁", "东京", "开封", "開封")),
    "shouchun": loc("寿春", "安徽省淮南市寿县", 116.7840, 32.5770, admin_id="CN-AH", precision="city", confidence=82, aliases=("寿春", "壽春", "寿县", "壽縣", "淮南")),
    "linzi": loc("临淄", "山东省淄博市临淄区", 118.3000, 36.8167, admin_id="CN-SD", precision="city", confidence=84, aliases=("临淄", "臨淄", "淄博", "齐国")),
    "dazexiang": loc("大泽乡", "安徽省宿州市埇桥区", 116.9841, 33.6339, admin_id="CN-AH", precision="region", confidence=78, aliases=("大泽乡", "大澤鄉", "宿州")),
    "mayi": loc("马邑", "山西省朔州市朔城区", 112.4329, 39.3316, admin_id="CN-SX", precision="city", confidence=78, aliases=("马邑", "馬邑", "朔州")),
    "hexi_jiuquan": loc("河西", "甘肃省酒泉市一带", 98.4943, 39.7326, admin_id="CN-GS", precision="region", confidence=74, aliases=("河西", "酒泉", "敦煌", "张掖", "武威")),
    "mobei_orhon": loc("漠北", "蒙古国鄂尔浑河流域", 102.8320, 47.2320, admin_id="MNG", precision="region", confidence=70, aliases=("漠北", "单于庭", "單于庭", "鄂尔浑", "於都斤", "于都斤")),
    "xiyu_luntai": loc("西域都护府", "新疆轮台县一带", 84.2510, 41.7780, admin_id="CN-XJ", precision="region", confidence=72, aliases=("西域都护", "西域都護", "轮台", "輪台", "乌垒", "烏壘")),
    "guangzong": loc("广宗", "河北省邢台市广宗县", 115.1430, 37.0750, admin_id="CN-HE", precision="city", confidence=76, aliases=("广宗", "廣宗", "巨鹿郡")),
    "julu": loc("巨鹿", "河北省邢台市平乡县、巨鹿县一带", 115.0300, 37.0600, admin_id="CN-HE", precision="region", confidence=78, aliases=("巨鹿", "鉅鹿", "平乡")),
    "gaixia": loc("垓下", "安徽省蚌埠市固镇县一带", 117.3200, 33.1800, admin_id="CN-AH", precision="region", confidence=76, aliases=("垓下", "固镇", "固鎮")),
    "guandu": loc("官渡", "河南省郑州市中牟县一带", 114.0200, 34.7200, admin_id="CN-HA", precision="region", confidence=79, aliases=("官渡", "中牟")),
    "chibi": loc("赤壁", "湖北省赤壁市一带", 113.9000, 29.7200, admin_id="CN-HB", precision="region", confidence=74, aliases=("赤壁", "蒲圻")),
    "xiangyang": loc("襄阳", "湖北省襄阳市", 112.1224, 32.0090, admin_id="CN-HB", precision="city", confidence=86, aliases=("襄阳", "襄陽", "襄樊")),
    "yiling": loc("夷陵", "湖北省宜昌市夷陵区", 111.2900, 30.7000, admin_id="CN-HB", precision="region", confidence=78, aliases=("夷陵", "猇亭", "宜昌")),
    "xuchang": loc("许", "河南省许昌市", 113.8526, 34.0355, admin_id="CN-HA", precision="city", confidence=88, aliases=("许昌", "許昌", "许都", "許都")),
    "chengdu": loc("成都", "四川省成都市", 104.0668, 30.5728, admin_id="CN-SC", precision="city", confidence=90, aliases=("成都",)),
    "jianye": loc("建业", "江苏省南京市", 118.7969, 32.0603, admin_id="CN-JS", precision="city", confidence=90, aliases=("建业", "建業", "建康", "应天府", "應天府", "天京", "南京")),
    "jiankang": loc("建康", "江苏省南京市", 118.7969, 32.0603, admin_id="CN-JS", precision="city", confidence=90, aliases=("建康", "南京", "天京")),
    "feishui": loc("淝水", "安徽省淮南市寿县一带", 116.7840, 32.5770, admin_id="CN-AH", precision="region", confidence=78, aliases=("淝水", "肥水", "寿县")),
    "guzang": loc("姑臧", "甘肃省武威市", 102.6380, 37.9280, admin_id="CN-GS", precision="city", confidence=82, aliases=("姑臧", "武威")),
    "datong_pingcheng": loc("平城", "山西省大同市", 113.3000, 40.0768, admin_id="CN-SX", precision="city", confidence=87, aliases=("平城", "大同")),
    "shengle": loc("盛乐", "内蒙古自治区和林格尔县", 111.8210, 40.3788, admin_id="CN-NM", precision="region", confidence=82, aliases=("盛乐", "盛樂", "和林格尔")),
    "hangzhou_linan": loc("临安", "浙江省杭州市", 120.1551, 30.2741, admin_id="CN-ZJ", precision="city", confidence=90, aliases=("临安", "臨安", "杭州")),
    "beijing": loc("北京", "北京市", 116.4074, 39.9042, admin_id="CN-BJ", precision="city", confidence=90, aliases=("北京", "大都", "中都", "燕京", "京师", "京師", "顺天府", "順天府")),
    "shenyang": loc("盛京", "辽宁省沈阳市", 123.4315, 41.8057, admin_id="CN-LN", precision="city", confidence=88, aliases=("盛京", "沈阳", "瀋陽")),
    "hetuala": loc("赫图阿拉", "辽宁省抚顺市新宾县", 125.0400, 41.7300, admin_id="CN-LN", precision="region", confidence=77, aliases=("赫图阿拉", "赫圖阿拉", "佛阿拉", "新宾", "抚顺")),
    "humen": loc("虎门", "广东省东莞市虎门镇", 113.6700, 22.8200, admin_id="CN-GD", precision="region", confidence=80, aliases=("虎门", "虎門")),
    "guangzhou": loc("广州", "广东省广州市", 113.2644, 23.1291, admin_id="CN-GD", precision="city", confidence=88, aliases=("广州", "廣州", "广东", "廣東")),
    "jintian": loc("金田", "广西壮族自治区桂平市金田镇", 110.0800, 23.5200, admin_id="CN-GX", precision="region", confidence=80, aliases=("金田", "桂平")),
    "tainan": loc("台湾府", "台湾台南市", 120.2020, 22.9999, admin_id="TWN", precision="city", confidence=82, aliases=("台南", "台湾府", "安平", "臺南", "臺灣府")),
    "yili": loc("伊犁", "新疆伊犁哈萨克自治州", 81.3240, 43.9160, admin_id="CN-XJ", precision="region", confidence=74, aliases=("伊犁", "伊犁将军", "伊犁將軍")),
    "wuchang": loc("武昌", "湖北省武汉市武昌区", 114.3050, 30.5928, admin_id="CN-HB", precision="city", confidence=86, aliases=("武昌", "武汉", "武漢")),
    "chengpu": loc("城濮", "山东省菏泽市鄄城县临濮一带", 115.5200, 35.5600, admin_id="CN-SD", precision="region", confidence=72, aliases=("城濮", "临濮", "鄄城")),
    "changping": loc("长平", "山西省高平市一带", 112.9300, 35.8000, admin_id="CN-SX", precision="region", confidence=76, aliases=("长平", "長平", "高平")),
    "sarhu": loc("萨尔浒", "辽宁省抚顺市东洲区萨尔浒一带", 123.9600, 41.8700, admin_id="CN-LN", precision="region", confidence=78, aliases=("萨尔浒", "薩爾滸")),
    "nerchinsk": loc("尼布楚", "俄罗斯涅尔琴斯克", 116.5800, 51.9800, admin_id="RUS", precision="city", confidence=76, aliases=("尼布楚", "涅尔琴斯克")),
    "shimonoseki": loc("马关", "日本山口县下关市", 130.9410, 33.9570, admin_id="JPN", precision="city", confidence=84, aliases=("马关", "馬關", "下关", "下關")),
    "asan_pungdo": loc("丰岛海域", "韩国牙山湾一带", 126.4500, 36.9300, admin_id="KOR", precision="region", confidence=74, aliases=("丰岛", "豐島", "牙山", "甲午")),
    "talas": loc("怛罗斯", "哈萨克斯坦塔拉兹一带", 71.3667, 42.9000, admin_id="KAZ", precision="region", confidence=72, aliases=("怛罗斯", "怛羅斯", "塔拉兹")),
    "onon": loc("斡难河", "蒙古国斡难河流域", 109.0000, 48.0000, admin_id="MNG", precision="region", confidence=68, aliases=("斡难河", "斡難河", "鄂嫩河")),
    "liujia": loc("刘家港", "江苏省太仓市浏河镇", 121.2700, 31.5100, admin_id="CN-JS", precision="region", confidence=78, aliases=("刘家港", "劉家港", "浏河", "太仓")),
    "yuegang": loc("月港", "福建省漳州市海澄一带", 117.8200, 24.4300, admin_id="CN-FJ", precision="region", confidence=76, aliases=("月港", "海澄", "漳州")),
    "kunming": loc("昆明", "云南省昆明市", 102.8329, 24.8801, admin_id="CN-YN", precision="city", confidence=84, aliases=("昆明", "云南", "雲南")),
    "yingzhou": loc("颍州", "安徽省阜阳市", 115.8140, 32.8900, admin_id="CN-AH", precision="city", confidence=78, aliases=("颍州", "潁州", "阜阳", "阜陽")),
    "heze": loc("曹州", "山东省菏泽市", 115.4800, 35.2300, admin_id="CN-SD", precision="city", confidence=76, aliases=("曹州", "菏泽", "菏澤")),
    "urumqi": loc("迪化", "新疆乌鲁木齐市", 87.6168, 43.8256, admin_id="CN-XJ", precision="city", confidence=78, aliases=("迪化", "乌鲁木齐", "烏魯木齊", "新疆")),
    "taiyuan": loc("太原", "山西省太原市", 112.5490, 37.8706, admin_id="CN-SX", precision="city", confidence=84, aliases=("太原", "晋阳", "晉陽")),
    "acheng": loc("上京会宁府", "黑龙江省哈尔滨市阿城区", 126.9750, 45.5390, admin_id="CN-HL", precision="region", confidence=82, aliases=("会宁府", "會寧府", "阿城", "哈尔滨")),
    "caizhou": loc("蔡州", "河南省驻马店市汝南县", 114.3500, 33.0000, admin_id="CN-HA", precision="city", confidence=76, aliases=("蔡州", "汝南", "驻马店")),
    "yamen": loc("崖山", "广东省江门市新会区崖门一带", 113.0600, 22.2100, admin_id="CN-GD", precision="region", confidence=78, aliases=("崖山", "崖门", "崖門", "江门")),
    "tumu": loc("土木堡", "河北省张家口市怀来县", 115.5200, 40.4000, admin_id="CN-HE", precision="region", confidence=79, aliases=("土木堡", "怀来", "懷來")),
    "chanzhou": loc("澶州", "河南省濮阳市", 115.0290, 35.7620, admin_id="CN-HA", precision="city", confidence=78, aliases=("澶州", "澶渊", "澶淵", "濮阳")),
    "dali": loc("羊苴咩城", "云南省大理市", 100.2300, 25.6920, admin_id="CN-YN", precision="city", confidence=82, aliases=("大理", "羊苴咩", "太和城")),
    "lhasa": loc("逻些", "西藏自治区拉萨市", 91.1170, 29.6580, admin_id="CN-XZ", precision="city", confidence=84, aliases=("逻些", "邏些", "拉萨", "拉薩")),
    "turpan_gaochang": loc("高昌", "新疆吐鲁番市高昌故城", 89.5310, 42.8530, admin_id="CN-XJ", precision="region", confidence=82, aliases=("高昌", "吐鲁番", "吐魯番")),
    "zhangye": loc("甘州", "甘肃省张掖市", 100.4500, 38.9260, admin_id="CN-GS", precision="city", confidence=82, aliases=("甘州", "张掖", "張掖")),
    "kaifeng": loc("汴梁", "河南省开封市", 114.3076, 34.7973, admin_id="CN-HA", precision="city", confidence=90, aliases=("汴梁", "开封", "開封", "东京")),
    "suzhou": loc("吴", "江苏省苏州市", 120.5853, 31.2989, admin_id="CN-JS", precision="city", confidence=82, aliases=("苏州", "蘇州", "吴县", "吳縣")),
    "wuxi": loc("梅里", "江苏省无锡市", 120.3119, 31.4912, admin_id="CN-JS", precision="city", confidence=78, aliases=("梅里", "无锡", "無錫")),
    "qufu": loc("曲阜", "山东省曲阜市", 116.9865, 35.5811, admin_id="CN-SD", precision="city", confidence=82, aliases=("曲阜", "鲁国", "魯國")),
    "yanling": loc("鄢", "河南省许昌市鄢陵县一带", 114.1910, 34.1023, admin_id="CN-HA", precision="region", confidence=72, aliases=("鄢", "鄢陵")),
    "xuge": loc("繻葛", "河南省许昌市长葛市一带", 113.7680, 34.2190, admin_id="CN-HA", precision="region", confidence=72, aliases=("繻葛", "𦈡葛", "长葛", "長葛")),
    "changshao": loc("长勺", "山东省济南市莱芜区一带", 117.6750, 36.2140, admin_id="CN-SD", precision="region", confidence=70, aliases=("长勺", "長勺", "莱芜", "萊蕪")),
    "beixing": loc("北杏", "山东省聊城市东阿县一带", 116.2480, 36.3350, admin_id="CN-SD", precision="region", confidence=64, aliases=("北杏", "东阿", "東阿")),
    "shaoling": loc("召陵", "河南省漯河市召陵区一带", 114.0910, 33.5860, admin_id="CN-HA", precision="region", confidence=74, aliases=("召陵", "漯河")),
    "guo_yu": loc("虞虢故地", "山西省平陆县至河南省三门峡市一带", 111.2100, 34.7700, admin_id="CN-SX", precision="region", confidence=66, aliases=("虞", "虢", "平陆", "三门峡")),
    "chen_huaiyang": loc("陈", "河南省周口市淮阳区一带", 114.8860, 33.7310, admin_id="CN-HA", precision="region", confidence=72, aliases=("陈国", "陳國", "淮阳", "淮陽")),
    "handan": loc("邯郸", "河北省邯郸市", 114.5391, 36.6256, admin_id="CN-HE", precision="city", confidence=82, aliases=("邯郸", "邯鄲")),
    "jiangling_ying": loc("郢", "湖北省荆州市江陵县一带", 112.1900, 30.3500, admin_id="CN-HB", precision="region", confidence=76, aliases=("郢", "江陵", "荆州", "荊州")),
    "kuaiji": loc("会稽", "浙江省绍兴市", 120.5802, 30.0303, admin_id="CN-ZJ", precision="city", confidence=78, aliases=("会稽", "會稽", "绍兴", "紹興", "越国")),
    "quwo": loc("曲沃", "山西省临汾市曲沃县", 111.4750, 35.6400, admin_id="CN-SX", precision="city", confidence=76, aliases=("曲沃", "翼城", "晋国")),
    "yongcheng": loc("雍城", "陕西省宝鸡市凤翔区", 107.4000, 34.5200, admin_id="CN-SN", precision="region", confidence=76, aliases=("雍城", "凤翔", "鳳翔", "秦国")),
    "jiyuan": loc("原", "河南省济源市", 112.6020, 35.0680, admin_id="CN-HA", precision="city", confidence=72, aliases=("济源", "濟源", "原国")),
    "anyang": loc("殷", "河南省安阳市", 114.3920, 36.0980, admin_id="CN-HA", precision="city", confidence=78, aliases=("安阳", "安陽", "殷国")),
    "pingdingshan": loc("应", "河南省平顶山市", 113.1926, 33.7662, admin_id="CN-HA", precision="city", confidence=74, aliases=("平顶山", "平頂山", "应国")),
    "liuan": loc("六", "安徽省六安市", 116.5200, 31.7350, admin_id="CN-AH", precision="city", confidence=72, aliases=("六安市", "六安", "六国")),
    "puyang": loc("帝丘", "河南省濮阳市", 115.0290, 35.7620, admin_id="CN-HA", precision="city", confidence=72, aliases=("濮阳", "濮陽", "卫国")),
    "shangqiu": loc("商丘", "河南省商丘市", 115.6560, 34.4150, admin_id="CN-HA", precision="city", confidence=74, aliases=("商丘", "宋国")),
    "juxian": loc("莒", "山东省莒县", 118.8370, 35.5800, admin_id="CN-SD", precision="city", confidence=72, aliases=("莒县", "莒縣", "莒国")),
    "xincai": loc("蔡", "河南省新蔡县", 114.9850, 32.7500, admin_id="CN-HA", precision="city", confidence=72, aliases=("新蔡", "上蔡", "蔡国")),
    "hancheng": loc("韩", "陕西省韩城市", 110.4420, 35.4770, admin_id="CN-SN", precision="city", confidence=70, aliases=("韩城", "韓城", "梁国")),
    "qishan": loc("岐山", "陕西省岐山县", 107.6210, 34.4430, admin_id="CN-SN", precision="city", confidence=70, aliases=("岐山", "扶风", "扶風")),
    "xian_province": loc("关中", "陕西省西安市一带", 108.9398, 34.3416, admin_id="CN-SN", precision="region", confidence=66, aliases=("陕西省", "陝西省", "关中")),
    "henan_region": loc("中原", "河南省郑州市一带", 113.6254, 34.7466, admin_id="CN-HA", precision="region", confidence=64, aliases=("河南省", "河南")),
    "shandong_region": loc("齐鲁", "山东省济南市一带", 117.1201, 36.6512, admin_id="CN-SD", precision="region", confidence=64, aliases=("山东省", "山東省")),
    "shanxi_region": loc("河东", "山西省太原市一带", 112.5490, 37.8706, admin_id="CN-SX", precision="region", confidence=64, aliases=("山西省", "山西")),
    "anhui_region": loc("江淮", "安徽省合肥市一带", 117.2272, 31.8206, admin_id="CN-AH", precision="region", confidence=64, aliases=("安徽省", "安徽")),
    "hebei_region": loc("河北", "河北省石家庄市一带", 114.5149, 38.0428, admin_id="CN-HE", precision="region", confidence=64, aliases=("河北省", "河北")),
    "jiangsu_region": loc("江南东部", "江苏省南京市一带", 118.7969, 32.0603, admin_id="CN-JS", precision="region", confidence=64, aliases=("江苏省", "江蘇省")),
    "zhejiang_region": loc("浙江", "浙江省杭州市一带", 120.1551, 30.2741, admin_id="CN-ZJ", precision="region", confidence=64, aliases=("浙江省", "浙江")),
    "hubei_region": loc("荆楚", "湖北省武汉市一带", 114.3050, 30.5928, admin_id="CN-HB", precision="region", confidence=64, aliases=("湖北省", "湖北")),
    "sichuan_region": loc("巴蜀", "四川省成都市一带", 104.0668, 30.5728, admin_id="CN-SC", precision="region", confidence=64, aliases=("四川省", "四川")),
    "gansu_region": loc("陇右", "甘肃省兰州市一带", 103.8343, 36.0611, admin_id="CN-GS", precision="region", confidence=64, aliases=("甘肃省", "甘肅省")),
    "neimeng_region": loc("漠南", "内蒙古自治区呼和浩特市一带", 111.7518, 40.8426, admin_id="CN-NM", precision="region", confidence=62, aliases=("内蒙古", "內蒙古")),
    "liaoning_region": loc("辽东", "辽宁省沈阳市一带", 123.4315, 41.8057, admin_id="CN-LN", precision="region", confidence=64, aliases=("辽宁省", "遼寧省", "辽东", "遼東")),
    "jilin_region": loc("吉林", "吉林省长春市一带", 125.3245, 43.8868, admin_id="CN-JL", precision="region", confidence=62, aliases=("吉林省", "吉林")),
    "heilongjiang_region": loc("黑龙江", "黑龙江省哈尔滨市一带", 126.6425, 45.7560, admin_id="CN-HL", precision="region", confidence=62, aliases=("黑龙江省", "黑龍江省")),
}

LOCATION_GAZETTEER.update({
    "nanjing": loc("南京", "江苏省南京市", 118.7969, 32.0603, admin_id="CN-JS", precision="city", confidence=90, aliases=("南京", "金陵", "建康")),
    "wuhan": loc("武汉", "湖北省武汉市", 114.3054, 30.5928, admin_id="CN-HB", precision="city", confidence=90, aliases=("武汉", "武漢", "汉口", "漢口", "武昌")),
    "chongqing": loc("重庆", "重庆市", 106.5516, 29.5630, admin_id="CN-CQ", precision="city", confidence=90, aliases=("重庆", "重慶", "陪都")),
    "ruijin": loc("瑞金", "江西省瑞金市", 116.0271, 25.8862, admin_id="CN-JX", precision="city", confidence=86, aliases=("瑞金", "中央苏区")),
    "yanan": loc("延安", "陕西省延安市", 109.4897, 36.5854, admin_id="CN-SN", precision="city", confidence=88, aliases=("延安", "延安时期")),
    "xibaipo": loc("西柏坡", "河北省平山县西柏坡", 114.1330, 38.3510, admin_id="CN-HE", precision="region", confidence=82, aliases=("西柏坡", "平山")),
    "xian": loc("西安", "陕西省西安市", 108.9398, 34.3416, admin_id="CN-SN", precision="city", confidence=90, aliases=("西安", "西京")),
    "changchun": loc("长春", "吉林省长春市", 125.3245, 43.8868, admin_id="CN-JL", precision="city", confidence=90, aliases=("长春", "新京", "長春")),
    "harbin": loc("哈尔滨", "黑龙江省哈尔滨市", 126.6425, 45.7560, admin_id="CN-HL", precision="city", confidence=88, aliases=("哈尔滨", "哈爾濱")),
    "dalian_lushun": loc("旅顺/大连", "辽宁省大连市旅顺口区及大连市区", 121.6147, 38.9140, admin_id="CN-LN", precision="region", confidence=82, aliases=("旅顺", "旅順", "大连", "大連", "关东州")),
    "qingdao": loc("青岛", "山东省青岛市", 120.3826, 36.0671, admin_id="CN-SD", precision="city", confidence=88, aliases=("青岛", "青島", "胶澳", "膠澳")),
    "weihai": loc("威海卫", "山东省威海市", 122.1204, 37.5131, admin_id="CN-SD", precision="city", confidence=86, aliases=("威海", "威海卫", "威海衛")),
    "zhanjiang": loc("广州湾", "广东省湛江市", 110.3594, 21.2707, admin_id="CN-GD", precision="city", confidence=84, aliases=("广州湾", "廣州灣", "湛江")),
    "shanghai": loc("上海", "上海市", 121.4737, 31.2304, admin_id="CN-SH", precision="city", confidence=90, aliases=("上海", "沪", "滬")),
    "tianjin": loc("天津", "天津市", 117.2000, 39.1333, admin_id="CN-TJ", precision="city", confidence=90, aliases=("天津", "天津租界")),
    "taipei": loc("台北", "台湾省台北市", 121.5654, 25.0330, admin_id="CN-TW", precision="city", confidence=88, aliases=("台北", "臺北")),
    "keelung": loc("基隆", "台湾省基隆市", 121.7392, 25.1276, admin_id="CN-TW", precision="city", confidence=84, aliases=("基隆",)),
    "hongkong": loc("香港", "香港特别行政区", 114.1694, 22.3193, admin_id="CN-HK", precision="city", confidence=90, aliases=("香港", "Hong Kong")),
    "macau": loc("澳门", "澳门特别行政区", 113.5439, 22.1987, admin_id="CN-MO", precision="city", confidence=88, aliases=("澳门", "澳門", "Macau")),
    "ulaanbaatar": loc("库伦", "蒙古国乌兰巴托", 106.9057, 47.8864, admin_id="MNG", precision="city", confidence=82, aliases=("库伦", "庫倫", "乌兰巴托", "烏蘭巴托", "外蒙古")),
    "zhangjiakou": loc("张家口", "河北省张家口市", 114.8841, 40.8119, admin_id="CN-HE", precision="city", confidence=86, aliases=("张家口", "張家口", "察哈尔")),
    "jinzhou": loc("锦州", "辽宁省锦州市", 121.1270, 41.0950, admin_id="CN-LN", precision="city", confidence=86, aliases=("锦州", "錦州")),
    "jinan": loc("济南", "山东省济南市", 117.1201, 36.6512, admin_id="CN-SD", precision="city", confidence=86, aliases=("济南", "濟南")),
    "nanchang": loc("南昌", "江西省南昌市", 115.8582, 28.6820, admin_id="CN-JX", precision="city", confidence=88, aliases=("南昌",)),
    "zunyi": loc("遵义", "贵州省遵义市", 106.9274, 27.7257, admin_id="CN-GZ", precision="city", confidence=86, aliases=("遵义", "遵義")),
    "luding": loc("泸定", "四川省泸定县", 102.2346, 29.9142, admin_id="CN-SC", precision="city", confidence=82, aliases=("泸定", "瀘定", "大渡河")),
    "lugouqiao": loc("卢沟桥", "北京市丰台区宛平城一带", 116.2130, 39.8490, admin_id="CN-BJ", precision="region", confidence=86, aliases=("卢沟桥", "盧溝橋", "宛平")),
    "taierzhuang": loc("台儿庄", "山东省枣庄市台儿庄区", 117.7342, 34.5636, admin_id="CN-SD", precision="region", confidence=84, aliases=("台儿庄", "臺兒莊", "枣庄")),
    "changsha": loc("长沙", "湖南省长沙市", 112.9388, 28.2282, admin_id="CN-HN", precision="city", confidence=88, aliases=("长沙", "長沙")),
    "hengyang": loc("衡阳", "湖南省衡阳市", 112.5720, 26.8930, admin_id="CN-HN", precision="city", confidence=86, aliases=("衡阳", "衡陽")),
    "xuzhou": loc("徐州", "江苏省徐州市", 117.2841, 34.2058, admin_id="CN-JS", precision="city", confidence=88, aliases=("徐州", "淮海")),
    "shijiazhuang": loc("石家庄", "河北省石家庄市", 114.5149, 38.0428, admin_id="CN-HE", precision="city", confidence=86, aliases=("石家庄", "石門", "石门")),
    "hefei": loc("合肥", "安徽省合肥市", 117.2272, 31.8206, admin_id="CN-AH", precision="city", confidence=86, aliases=("合肥",)),
    "fuzhou": loc("福州", "福建省福州市", 119.2965, 26.0745, admin_id="CN-FJ", precision="city", confidence=86, aliases=("福州",)),
    "lanzhou": loc("兰州", "甘肃省兰州市", 103.8343, 36.0611, admin_id="CN-GS", precision="city", confidence=86, aliases=("兰州", "蘭州")),
    "cairo": loc("开罗", "埃及开罗", 31.2357, 30.0444, admin_id="EGY", precision="city", confidence=84, aliases=("开罗", "開羅", "Cairo")),
})

POLITY_LOCATION_KEYS = {
    "西周": "haojing",
    "东周": "luoyi",
    "周国": "xian_province",
    "东周国": "luoyi",
    "西周国": "henan_region",
    "齐国": "linzi",
    "鲁国": "qufu",
    "晋国": "quwo",
    "秦国": "yongcheng",
    "楚国": "jiangling_ying",
    "吴国": "suzhou",
    "越国": "kuaiji",
    "燕国": "beijing",
    "韩国": "xinzheng",
    "赵国": "handan",
    "魏国": "daliang",
    "秦朝": "xianyang",
    "西汉": "changan",
    "新朝": "changan",
    "东汉": "luoyang",
    "曹魏": "luoyang",
    "蜀汉": "chengdu",
    "东吴": "jianye",
    "西晋": "luoyang",
    "东晋": "jiankang",
    "北魏": "datong_pingcheng",
    "隋朝": "changan",
    "唐朝": "changan",
    "北宋": "kaifeng",
    "南宋": "hangzhou_linan",
    "辽朝": "mobei_orhon",
    "金朝": "acheng",
    "西夏": "gansu_region",
    "元朝": "beijing",
    "明朝": "jianye",
    "后金": "hetuala",
    "清朝": "shenyang",
    "明郑": "tainan",
    "太平天国": "jintian",
    "吐蕃": "lhasa",
    "南诏": "dali",
    "大理": "dali",
    "高昌回鹘": "turpan_gaochang",
    "甘州回鹘": "zhangye",
}

POLITY_LOCATION_KEYS.update({
    "中华民国临时政府": "nanjing",
    "中华民国北京政府": "beijing",
    "北洋军阀实际控制区": "beijing",
    "广州护法军政府": "guangzhou",
    "中华民国国民政府（名义层）": "nanjing",
    "国民政府实际控制区": "nanjing",
    "中华苏维埃共和国": "ruijin",
    "陕甘宁边区与中共抗日根据地": "yanan",
    "中国共产党解放区": "xibaipo",
    "满洲国": "changchun",
    "中华民国临时政府（华北）": "beijing",
    "中华民国维新政府": "nanjing",
    "汪精卫南京国民政府": "nanjing",
    "蒙疆联合自治政府": "zhangjiakou",
    "日本台湾总督府": "taipei",
    "日本关东州租借地": "dalian_lushun",
    "英租威海卫": "weihai",
    "法租广州湾": "zhanjiang",
    "日本占领胶澳青岛": "qingdao",
    "上海公共租界": "shanghai",
    "上海法租界": "shanghai",
    "天津租界群": "tianjin",
    "英属香港": "hongkong",
    "日占香港": "hongkong",
    "英属香港（战后恢复）": "hongkong",
    "葡属澳门": "macau",
    "外蒙古/蒙古人民共和国": "ulaanbaatar",
    "西藏噶厦政权": "lhasa",
    "新疆省地方军政": "urumqi",
    "新疆三区革命政权": "yili",
    "中华人民共和国（1949年成立）": "beijing",
})

EVENT_LOCATION_KEYS = {
    "event_0001": "muye",
    "event_0002": "haojing",
    "event_0003": "luoyi",
    "event_0004": "luoyang",
    "event_0005": "luoyang",
    "event_0006": "xinzheng",
    "event_0007": "daliang",
    "event_0008": "shouchun",
    "event_0009": "linzi",
    "event_0010": "dazexiang",
    "event_0011": "xianyang",
    "event_0012": "changan",
    "event_0013": "mayi",
    "event_0014": "hexi_jiuquan",
    "event_0015": "mobei_orhon",
    "event_0016": "xiyu_luntai",
    "event_0017": "changan",
    "event_0018": "luoyang",
    "event_0019": "guangzong",
    "event_0020": "chibi",
    "event_0021": "luoyang",
    "event_0022": "jianye",
    "event_0023": "luoyang",
    "event_0024": "jiankang",
    "event_0025": "feishui",
    "event_0026": "guzang",
    "event_0027": "changan",
    "event_0028": "jiankang",
    "event_0029": "changan",
    "event_0030": "changan",
    "event_0031": "beijing",
    "event_0032": "kaifeng",
    "event_0033": "kaifeng",
    "event_0034": "taiyuan",
    "event_0035": "chanzhou",
    "event_0036": "acheng",
    "event_0037": "kaifeng",
    "event_0038": "caizhou",
    "event_0039": "beijing",
    "event_0040": "yamen",
    "event_0041": "jianye",
    "event_0042": "tumu",
    "event_0043": "hetuala",
    "event_0044": "shenyang",
    "event_0045": "beijing",
    "event_0046": "tainan",
    "event_0047": "yili",
    "event_0048": "guangzhou",
    "event_0049": "jintian",
    "event_0050": "beijing",
    "event_0051": "wuchang",
    "event_0052": "beijing",
}

PRE_QIN_SOURCES = ("《左传》|《史记》", "https://ctext.org/chun-qiu-zuo-zhuan/zh|https://ctext.org/shiji/zh")
QIN_HAN_SOURCES = ("《史记》|《汉书》", "https://ctext.org/shiji/zh|https://ctext.org/han-shu/zh")
TONGJIAN_SOURCES = ("《资治通鉴》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/zizhi-tongjian/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml")
TANG_SOURCES = ("《旧唐书》|《资治通鉴》", "https://ctext.org/jiu-tang-shu/zh|https://ctext.org/zizhi-tongjian/zh")
SONG_SOURCES = ("《宋史》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/song-shi/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml")
MING_SOURCES = ("《明史》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/ming-shi/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml")
QING_SOURCES = ("《清史稿》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/qing-shi-gao/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml")
REPUBLIC_SOURCES = (
    "Encyclopaedia Britannica: Republican China 1911-49|Office of the Historian: The Chinese Revolution of 1949",
    "https://www.britannica.com/place/China/Republican-China-1911-49|https://history.state.gov/milestones/1945-1952/chinese-rev",
)
REPUBLIC_CIVIL_WAR_SOURCES = (
    "Encyclopaedia Britannica: Chinese Civil War|Office of the Historian: The Chinese Revolution of 1949",
    "https://www.britannica.com/event/Chinese-Civil-War|https://history.state.gov/milestones/1945-1952/chinese-rev",
)
REPUBLIC_WAR_JAPAN_SOURCES = (
    "Encyclopaedia Britannica: Second Sino-Japanese War|Office of the Historian: Japan Surrenders and World War II Ends",
    "https://www.britannica.com/event/Second-Sino-Japanese-War|https://history.state.gov/milestones/1937-1945/japan-surrender",
)
REPUBLIC_BORDER_SOURCES = (
    "Encyclopaedia Britannica: Mongolia Between Russia and China|Encyclopaedia Britannica: Tibet since 1900",
    "https://www.britannica.com/place/Mongolia/Between-Russia-and-China|https://www.britannica.com/place/Tibet/Tibet-since-1900",
)
REPUBLIC_TREATY_SOURCES = (
    "Avalon Project: Cairo Communique 1943|Avalon Project: Potsdam Declaration 1945",
    "https://avalon.law.yale.edu/wwii/cairo.asp|https://avalon.law.yale.edu/20th_century/decade17.asp",
)
REPUBLIC_LEASE_SOURCES = (
    "Encyclopaedia Britannica: Shanghai History|Encyclopaedia Britannica: Hong Kong History",
    "https://www.britannica.com/place/Shanghai/History|https://www.britannica.com/place/Hong-Kong/History",
)
COURSE_AND_TIMELINE_SOURCES = (
    "《义务教育历史课程标准（2022年版）》|中国社会科学出版社《中国历史年表数据库》",
    "https://www.htu.edu.cn/history/2022/0905/c18511a251113/page.htm|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml",
)


def anchor(
    anchor_id: str,
    start_year: int,
    end_year: int,
    title: str,
    description: str,
    location_key: str,
    *,
    stage: str = "初中",
    event_type: str = "range_anchor",
    source_pair: tuple[str, str] = COURSE_AND_TIMELINE_SOURCES,
    related_polity_ids: tuple[str, ...] = (),
    importance: int = 2,
    priority: int = 5,
) -> dict[str, Any]:
    return {
        "anchor_id": anchor_id,
        "start_year": start_year,
        "end_year": end_year,
        "title": title,
        "description": description,
        "location_key": location_key,
        "stage": stage,
        "event_type": event_type,
        "source_titles": source_pair[0],
        "source_urls": source_pair[1],
        "related_polity_ids": list(related_polity_ids),
        "importance_level": importance,
        "display_priority": priority,
    }


RANGE_ANCHOR_SPECS = [
    anchor("western_zhou_order", -1046, -842, "西周分封与礼乐秩序", "这一阶段，周王室以镐京为中心推行分封、宗法和礼乐秩序，诸侯网络逐步成形。", "haojing", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0129",)),
    anchor("late_western_zhou_crisis", -841, -771, "西周晚期王室危机", "这一阶段，周王室威望下降，关中政治危机加深，最终引发平王东迁前后的秩序重组。", "haojing", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0129",)),
    anchor("spring_autumn_hegemony", -770, -476, "春秋诸侯会盟与争霸", "这一阶段，周天子名义仍在洛邑，齐、晋、楚、秦等诸侯通过会盟和战争争夺主导权。", "luoyi", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0003",)),
    anchor("warring_states_reforms", -475, -221, "战国变法与兼并战争", "这一阶段，各国推行变法、扩军和县制治理，秦国在兼并战争中逐步取得优势。", "xianyang", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0109",)),
    anchor("qin_unification_system", -220, -207, "秦制推行与天下一统", "这一阶段，秦朝从咸阳推行郡县、统一文字度量衡和驰道体系，也激化了沉重徭役与反秦矛盾。", "xianyang", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0110",)),
    anchor("chu_han_war", -206, -203, "楚汉战争", "这一阶段，刘邦与项羽围绕关中、彭城和中原反复争夺，汉政权在战争中逐渐占上风。", "changan", source_pair=QIN_HAN_SOURCES),
    anchor("early_western_han", -202, -141, "西汉郡国并行与休养生息", "这一阶段，西汉以长安为中心恢复生产，郡县与诸侯国并行，国家财政和社会秩序逐步稳定。", "changan", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",)),
    anchor("han_wudi_expansion", -140, -87, "汉武帝时期内外经营", "这一阶段，汉廷加强中央集权，北击匈奴、通西域、经营河西，帝国边疆明显拓展。", "changan", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",)),
    anchor("late_western_han", -86, 8, "西汉后期政治调整", "这一阶段，西汉在外戚、儒学政治和财政压力之间调整治理，王莽最终掌握朝政。", "changan", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",)),
    anchor("xin_wangmang_reform", 9, 23, "新莽改制与社会动荡", "这一阶段，王莽在长安推行复古改制，币制和土地政策反复变动，地方起义不断扩大。", "changan", source_pair=("《汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0071",)),
    anchor("post_xin_transition", 24, 24, "新莽覆亡后的更始过渡", "这一年，新莽已亡，更始政权与各地军事势力围绕关中、洛阳和河北重新争夺秩序。", "changan", source_pair=("《汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml")),
    anchor("early_eastern_han", 25, 105, "东汉重建与西域经营", "这一阶段，东汉以洛阳为中心重建秩序，豪强大族壮大，朝廷多次恢复同西域的联系。", "luoyang", source_pair=("《后汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/hou-han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0006",)),
    anchor("late_eastern_han", 106, 184, "东汉后期外戚宦官与地方豪强", "这一阶段，洛阳朝廷在外戚、宦官和士人冲突中反复摇摆，地方豪强势力日益增强。", "luoyang", source_pair=("《后汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/hou-han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0006",)),
    anchor("han_warlord_transition", 185, 220, "东汉末年群雄割据", "这一阶段，黄巾起义后州郡武装坐大，曹操、孙氏、刘备等势力在战争中形成三国格局。", "xuchang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0006",)),
    anchor("three_kingdoms_balance", 221, 263, "三国鼎立与南北攻守", "这一阶段，魏、蜀、吴分别控制北方、巴蜀和江东，战争与外交围绕荆州、淮南和汉中展开。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0075", "polity_0127", "polity_0002")),
    anchor("wei_wu_duality", 264, 265, "魏吴对峙与蜀汉覆亡后局势", "这一阶段，蜀汉已亡，曹魏与东吴分别控制北方和江东，司马氏掌握魏政并完成代魏前夜的权力转换。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0075", "polity_0002")),
    anchor("jin_wu_duality", 266, 280, "西晋代魏与晋吴对峙", "这一阶段，西晋取代曹魏后与东吴南北对峙，直到280年晋军灭吴，三国归晋。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0132", "polity_0002")),
    anchor("western_jin_transition", 281, 316, "西晋统一后的门阀政治与内乱", "这一阶段，西晋短暂统一后，宗室争权和地方军镇动荡不断扩大，北方秩序迅速瓦解。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0132",)),
    anchor("eastern_jin_sixteen_kingdoms", 317, 420, "东晋十六国南北分裂", "这一阶段，建康东晋维持江南政权，北方多个族群政权更替，南北政治格局长期分裂。", "jiankang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0005",)),
    anchor("northern_wei_unification", 421, 439, "北魏统一北方", "这一阶段，北魏从平城向黄河流域推进，陆续兼并北方诸政权，为南北朝对峙奠定基础。", "datong_pingcheng", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0030",)),
    anchor("northern_wei_southern_dynasties", 440, 534, "北魏与南朝对峙", "这一阶段，北魏与南朝宋、齐、梁长期对峙，北方均田、迁都与汉化改革和江南士族政治并行发展。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0030",)),
    anchor("east_west_wei_liang", 535, 550, "东西魏分立与梁朝并存", "这一阶段，北魏分裂为东魏、西魏，南方梁朝仍以建康为中心，南北政治格局进入多方并立。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0008", "polity_0139", "polity_0083")),
    anchor("late_liang_western_wei_northern_qi", 551, 557, "梁末动荡与西魏北齐并立", "这一阶段，梁朝内乱削弱南方政权，北方西魏、北齐并立，长江与关陇局势同时重组。", "jiankang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0083", "polity_0139", "polity_0031")),
    anchor("northern_qi_zhou_chen", 558, 577, "北齐北周陈三方对峙", "这一阶段，陈朝据守江南，北齐、北周在北方竞争，关中与河北的军政整合影响统一走向。", "luoyang", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0031", "polity_0025", "polity_0157")),
    anchor("northern_zhou_chen_sui_transition", 578, 581, "北周陈对峙与隋代周前夜", "这一阶段，北周灭北齐后控制北方，南方陈朝延续，杨坚掌握北周政局并走向代周建隋。", "changan", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0025", "polity_0157")),
    anchor("sui_unification_canal", 582, 618, "隋朝统一与制度工程", "这一阶段，隋朝完成南北统一，建设大运河、完善科举和三省六部，但大规模徭役加剧社会压力。", "changan", source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0158",)),
    anchor("tang_early_middle", 619, 755, "唐前中期国家治理与边疆秩序", "这一阶段，唐朝以长安为中心发展科举、律令和均田府兵制度，并同突厥、吐蕃、西域频繁互动。", "changan", source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",)),
    anchor("tang_late_fanzhen", 756, 907, "唐后期藩镇与财政变革", "这一阶段，安史之乱后藩镇割据加重，朝廷通过两税法等方式维持财政和中央权威。", "changan", source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",)),
    anchor("later_liang_ten_kingdoms", 908, 923, "后梁与十国并立", "这一阶段，后梁控制中原，南方多个政权并立，唐末藩镇格局继续影响财政与军事。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0048",)),
    anchor("later_tang_ten_kingdoms", 924, 936, "后唐与十国并立", "这一阶段，后唐取代后梁成为北方核心政权，南方割据政权继续并存。", "luoyang", source_pair=SONG_SOURCES, related_polity_ids=("polity_0046",)),
    anchor("later_jin_ten_kingdoms", 937, 947, "后晋与十国并立", "这一阶段，后晋依托契丹支持立国，燕云问题和北方边疆压力更加突出。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0047",)),
    anchor("later_han_ten_kingdoms", 948, 950, "后汉与十国并立", "这一阶段，后汉短暂控制中原，军政集团更替速度加快。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0049",)),
    anchor("later_zhou_reform_unification", 951, 960, "后周改革与宋初统一前夜", "这一阶段，后周整顿军政并向南北推进，为北宋建立后的统一行动奠定基础。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0045",)),
    anchor("early_northern_song", 961, 1004, "宋初统一与文官政治", "这一阶段，北宋从开封推进统一，强化中央禁军和文官制度，逐步结束五代十国分裂。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0026",)),
    anchor("song_liao_and_tangut_rise", 1005, 1037, "宋辽对峙与党项崛起", "这一阶段，北宋与辽维持澶渊之盟后的对峙互市，党项势力在西北持续扩张。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0026", "polity_0146")),
    anchor("song_liao_xia", 1038, 1114, "宋辽西夏三方并立", "这一阶段，北宋、辽、西夏三方并立，和战、岁币与边疆互市共同塑造北方秩序。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0026", "polity_0146", "polity_0131")),
    anchor("song_liao_xia_jin_overlap", 1115, 1125, "宋辽夏金短期并立", "这一阶段，金朝兴起并迅速挑战辽朝，北宋、西夏与东北新兴女真政权同处剧变格局。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0026", "polity_0146", "polity_0131", "polity_0154")),
    anchor("jin_southward_northern_song_crisis", 1126, 1127, "金军南下与北宋危机", "这一阶段，金军南下攻破东京，北宋政治中心崩溃，宋金格局转向南北对峙。", "kaifeng", source_pair=SONG_SOURCES, related_polity_ids=("polity_0026", "polity_0131", "polity_0154")),
    anchor("southern_song_jin_xia", 1128, 1227, "南宋金西夏对峙", "这一阶段，南宋经营江南，金控制华北，西夏维持西北政权，三方格局长期延续。", "hangzhou_linan", source_pair=SONG_SOURCES, related_polity_ids=("polity_0034", "polity_0154", "polity_0131")),
    anchor("southern_song_jin_mongol_pressure", 1228, 1234, "南宋金对峙与蒙古压力", "这一阶段，蒙古持续南下压迫金朝，南宋与金朝的旧有边界秩序走向瓦解。", "hangzhou_linan", source_pair=SONG_SOURCES, related_polity_ids=("polity_0034", "polity_0154")),
    anchor("southern_song_mongol_war", 1235, 1270, "南宋抗蒙战争", "这一阶段，南宋与蒙古长期作战，四川、襄阳和长江防线成为决定南方存亡的关键。", "hangzhou_linan", source_pair=SONG_SOURCES, related_polity_ids=("polity_0034",)),
    anchor("southern_song_yuan_final", 1271, 1279, "南宋与元朝最后对峙", "这一阶段，元朝定国号后持续南下，南宋从临安失守走向崖山覆亡。", "hangzhou_linan", source_pair=SONG_SOURCES, related_polity_ids=("polity_0034", "polity_0013")),
    anchor("yuan_governance", 1280, 1368, "元代统一治理与交通交流", "这一阶段，元朝以大都为中心实行行省制度，欧亚交通和多族群互动显著加强。", "beijing", source_pair=("《元史》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/yuan-shi/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0013",)),
    anchor("early_ming_institutions", 1369, 1421, "明初制度重建与海上交流", "这一阶段，明朝重建赋役、卫所和科举制度，南京、北京之间的政治重心逐步调整。", "jianye", source_pair=MING_SOURCES, related_polity_ids=("polity_0072",)),
    anchor("middle_ming_governance", 1422, 1566, "明中期内阁财政与边防", "这一阶段，明朝以内阁协助政务，北方边防、南方赋役和海禁走私共同牵动国家治理。", "beijing", source_pair=MING_SOURCES, related_polity_ids=("polity_0072",)),
    anchor("late_ming_transition", 1567, 1644, "明后期改革、海贸与财政危机", "这一阶段，白银流通、张居正改革、辽东战争和农民起义交织，明朝财政与军事压力持续上升。", "beijing", source_pair=MING_SOURCES, related_polity_ids=("polity_0072",)),
    anchor("early_qing_unification", 1645, 1683, "清初统一战争与海疆整合", "这一阶段，清廷以北京为中心平定各地抵抗，处理三藩、台湾和边疆问题，统一秩序逐步形成。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    anchor("qing_high_empire", 1684, 1759, "康雍乾治理与边疆经营", "这一阶段，清朝通过军机、摊丁入亩、改土归流和西北用兵加强中央治理与边疆控制。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    anchor("late_qing_society_pressure", 1760, 1838, "清中后期人口增长与社会压力", "这一阶段，人口、土地、财政和秘密结社问题加重，沿海贸易与鸦片输入逐渐冲击清朝秩序。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    anchor("late_qing_wars_rebellions", 1839, 1864, "晚清内忧外患", "这一阶段，鸦片战争、太平天国和地方团练兴起相互交织，清朝被迫面对内政与外交双重危机。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    anchor("self_strengthening_border", 1865, 1895, "洋务、边疆与海防", "这一阶段，清廷推动洋务企业和新式海防，同时处理西北、东南海疆和中外条约压力。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    anchor("late_qing_reform_revolution", 1896, 1912, "清末变法新政与革命", "这一阶段，清廷在列强压力和国内改革呼声中推行新政，革命力量最终推动帝制结束。", "beijing", source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
]

RANGE_ANCHOR_SPECS.extend([
    anchor("republic_beiyang_warlord", 1913, 1927, "北京政府、护法与军阀政治", "这一阶段，中华民国北京政府保有外交代表性，南方护法政权与北洋各派军阀并立，实际控制区频繁变化。", "beijing", source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0185", "polity_0186")),
    anchor("republic_nationalist_unification", 1928, 1931, "南京国民政府与名义统一", "这一阶段，北伐和东北易帜后南京国民政府取得较广泛承认，但地方实力派、边疆自治与租界仍限制实际统一。", "nanjing", source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    anchor("republic_manchuria_soviets", 1932, 1936, "东北沦陷、苏区与南京十年", "这一阶段，满洲国在东北形成，日本势力扩张；国民政府推进南京十年建设，中共苏区经历围剿与长征。", "nanjing", source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0189", "polity_0192")),
    anchor("republic_total_war_initial", 1937, 1940, "全面抗战初期三方格局", "这一阶段，重庆国民政府、日占区傀儡政权和中共敌后根据地并存，华北、华中与沿海控制区迅速重组。", "chongqing", source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0190", "polity_0193", "polity_0194", "polity_0195")),
    anchor("republic_total_war_late", 1941, 1945, "太平洋战争与战后接收前夜", "这一阶段，日本占领香港和东南亚战场扩大，中国战场进入持久消耗；盟国声明和日本投降决定战后接收框架。", "chongqing", source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0190", "polity_0195", "polity_0206")),
    anchor("republic_postwar_reception_civilwar", 1946, 1947, "战后接收与全面内战重启", "这一阶段，国民政府接收台湾、东北和日占区后，国共谈判破裂，全面内战在东北、华北和中原展开。", "nanjing", source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0191")),
    anchor("republic_final_campaigns", 1948, 1949, "战略决战与政权转移", "这一阶段，辽沈、淮海、平津三大战役和渡江战役改变大陆控制格局，中华人民共和国成立，中华民国中央政府迁往台湾。", "beijing", source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0191", "polity_0213")),
])


def supp(
    event_id: str,
    year: int,
    sort_order: int,
    event_type: str,
    title: str,
    description: str,
    location_key: str,
    *,
    stage: str = "初中",
    importance: int = 4,
    priority: int = 2,
    related_polity_ids: tuple[str, ...] = (),
    related_people: tuple[str, ...] = (),
    source_pair: tuple[str, str] = TONGJIAN_SOURCES,
    significance: str = "",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "year": year,
        "sort_order": sort_order,
        "event_type": event_type,
        "title": title,
        "description": description,
        "significance": significance or description,
        "location_key": location_key,
        "stage": stage,
        "importance_level": importance,
        "display_priority": priority,
        "related_polity_ids": list(related_polity_ids),
        "related_people": list(related_people),
        "source_titles": source_pair[0],
        "source_urls": source_pair[1],
    }


SUPPLEMENTAL_EVENT_SPECS = [
    supp("supp_m841_guoren", -841, 20, "event", "国人暴动与共和行政", "前841年，镐京国人起事，周厉王出奔，共和行政开始。", "haojing", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0129",)),
    supp("supp_m722_zheng_ke_duan", -722, 20, "event", "郑伯克段于鄢", "前722年，郑庄公平定共叔段之乱，郑国君位与宗族冲突公开化。", "yanling", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0150",), related_people=("郑庄公", "共叔段")),
    supp("supp_m719_wei_zhouxu", -719, 20, "event", "卫州吁之乱", "前719年，卫国州吁弑杀卫桓公自立，随后被陈国拘捕并由卫人处死。", "puyang", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0040", "polity_0156"), related_people=("州吁", "石碏")),
    supp("supp_m707_xuge", -707, 20, "war", "繻葛之战", "前707年，周桓王率蔡、卫、陈伐郑，在繻葛被郑军击败，周王室权威受挫。", "xuge", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0003", "polity_0150", "polity_0124", "polity_0040", "polity_0156"), related_people=("周桓王", "郑庄公")),
    supp("supp_m704_chu_wuwang_king", -704, 20, "event", "楚武王称王", "前704年前后，楚君熊通自称武王，显示楚国脱离周王室爵命体系并向汉东扩张。", "hubei_region", stage="高中", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0084",), related_people=("楚武王",)),
    supp("supp_m701_zheng_succession", -701, 20, "event", "郑庄公卒与郑国内乱", "前701年，郑庄公去世后，祭仲被宋人胁迫立公子突，郑昭公出奔，郑国内乱开始。", "xinzheng", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0150", "polity_0061"), related_people=("郑庄公", "祭仲", "郑厉公", "郑昭公")),
    supp("supp_m700_lu_zheng_song", -700, 20, "war", "鲁郑伐宋", "前700年，鲁桓公与郑厉公在武父盟后伐宋，鲁、郑、宋关系继续恶化。", "shangqiu", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0166", "polity_0150", "polity_0061"), related_people=("鲁桓公", "郑厉公", "宋庄公")),
    supp("supp_m699_ji_war", -699, 20, "war", "纪之战", "前699年，纪、鲁、郑联军与齐、宋、卫、燕交战，齐、宋、卫、燕诸军败绩。", "shandong_region", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0166", "polity_0150", "polity_0167", "polity_0061", "polity_0040", "polity_0104")),
    supp("supp_m694_lu_huan_qi", -694, 20, "event", "鲁桓公薨于齐", "前694年，鲁桓公随夫人文姜至齐，随后在齐国遇害，鲁齐关系震动。", "linzi", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0166", "polity_0167"), related_people=("鲁桓公", "齐襄公", "文姜")),
    supp("supp_m686_qi_xiang_murder", -686, 20, "event", "齐襄公被弑", "前686年，齐襄公在齐国内乱中被杀，公孙无知短暂执政，齐国君位危机爆发。", "linzi", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0167",), related_people=("齐襄公", "公孙无知")),
    supp("supp_m685_qi_huan_accession", -685, 20, "event", "齐桓公即位与管仲入相", "前685年，公子小白即位为齐桓公，鲍叔牙荐管仲，齐国霸业由此展开。", "linzi", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0167",), related_people=("齐桓公", "管仲", "鲍叔牙")),
    supp("supp_m684_changshao", -684, 20, "war", "长勺之战", "前684年，齐军伐鲁，鲁庄公在曹刿辅佐下于长勺击败齐军。", "changshao", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0166", "polity_0167"), related_people=("鲁庄公", "曹刿")),
    supp("supp_m681_beixing", -681, 20, "diplomacy", "北杏会盟", "前681年，齐桓公会宋、陈、蔡、邾等诸侯于北杏，齐国开始以会盟主导诸侯。", "beixing", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0167", "polity_0061", "polity_0156", "polity_0124"), related_people=("齐桓公",)),
    supp("supp_m656_zhaoling", -656, 20, "diplomacy", "召陵之盟", "前656年，齐桓公率诸侯伐楚，双方于召陵结盟，尊王攘夷格局成形。", "shaoling", stage="高中", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0167", "polity_0084", "polity_0124"), related_people=("齐桓公", "楚成王")),
    supp("supp_m655_jin_fake_way", -655, 20, "war", "晋假道灭虢虞", "前655年，晋献公借道虞国伐虢，灭虢后回师灭虞，河东格局重组。", "guo_yu", stage="高中", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0073", "polity_0126", "polity_0137", "polity_0029"), related_people=("晋献公", "宫之奇")),
    supp("supp_m632_chengpu", -632, 20, "war", "城濮之战", "前632年，晋、楚在城濮交战，晋文公取胜并称霸诸侯。", "chengpu", source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0073", "polity_0084"), related_people=("晋文公",)),
    supp("supp_m356_shangyang", -356, 20, "reform", "商鞅变法", "前356年，商鞅在秦孝公支持下推行变法，秦国国力迅速增强。", "liyang", stage="高中", importance=5, priority=1, source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0109",), related_people=("商鞅", "秦孝公")),
    supp("supp_m260_changping", -260, 20, "war", "长平之战", "前260年，秦赵在长平决战，赵军大败，秦统一六国的阻力大减。", "changping", stage="高中", importance=5, priority=1, source_pair=PRE_QIN_SOURCES, related_polity_ids=("polity_0109", "polity_0144"), related_people=("白起",)),
    supp("supp_m207_julu", -207, 15, "war", "巨鹿之战", "前207年，项羽在巨鹿击破秦军主力，秦朝迅速走向崩溃。", "julu", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0110",), related_people=("项羽",)),
    supp("supp_m202_gaixia", -202, 15, "war", "垓下之战", "前202年，刘邦、韩信等在垓下围困项羽，楚汉战争结束。", "gaixia", source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",), related_people=("刘邦", "项羽", "韩信")),
    supp("supp_m154_qiguo", -154, 20, "war", "七国之乱", "前154年，吴王刘濞等七国起兵反汉，汉景帝派周亚夫平定叛乱。", "changan", stage="高中", importance=4, priority=2, source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",), related_people=("汉景帝", "周亚夫")),
    supp("supp_m138_zhangqian", -138, 20, "diplomacy", "张骞出使西域", "前138年，张骞从长安出发通西域，为汉朝经营西北打开道路。", "changan", importance=5, priority=1, source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",), related_people=("张骞",)),
    supp("supp_m106_cishi", -106, 20, "institution", "汉武帝设十三刺史部", "前106年，汉武帝分设十三刺史部，加强朝廷对地方的监察。", "changan", stage="高中", importance=4, priority=2, source_pair=QIN_HAN_SOURCES, related_polity_ids=("polity_0134",), related_people=("汉武帝",)),
    supp("supp_p73_banchao", 73, 20, "diplomacy", "班超经营西域", "73年，班超出使西域，东汉重新打通同西域诸国的联系。", "luoyang", stage="高中", importance=4, priority=2, source_pair=("《后汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/hou-han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0006",), related_people=("班超",)),
    supp("supp_p105_paper", 105, 20, "culture", "蔡伦改进造纸术", "105年，蔡伦向朝廷献上改进后的造纸方法，纸逐渐成为重要书写材料。", "luoyang", importance=5, priority=1, source_pair=("《后汉书》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/hou-han-shu/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0006",), related_people=("蔡伦",)),
    supp("supp_p200_guandu", 200, 20, "war", "官渡之战", "200年，曹操在官渡击败袁绍，北方格局转向曹操一方。", "guandu", importance=5, priority=1, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0006",), related_people=("曹操", "袁绍")),
    supp("supp_p219_xiangfan", 219, 20, "war", "襄樊之战", "219年，关羽围攻襄樊，随后败走麦城，荆州形势逆转。", "xiangyang", stage="高中", importance=4, priority=2, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0006",), related_people=("关羽",)),
    supp("supp_p221_liubei", 221, 20, "dynasty_start", "刘备称帝", "221年，刘备在成都称帝，蜀汉建立。", "chengdu", importance=4, priority=1, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0127",), related_people=("刘备",)),
    supp("supp_p222_yiling", 222, 20, "war", "夷陵之战", "222年，陆逊在夷陵击败刘备，蜀汉东出受挫。", "yiling", importance=4, priority=2, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0127", "polity_0002"), related_people=("陆逊", "刘备")),
    supp("supp_p263_weishuhan", 263, 20, "war", "魏灭蜀汉", "263年，魏军攻入成都，刘禅投降，蜀汉灭亡。", "chengdu", importance=4, priority=1, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0075", "polity_0127"), related_people=("刘禅", "邓艾")),
    supp("supp_p291_bawang", 291, 20, "event", "八王之乱开始", "291年，西晋宗室争权激化，八王之乱从洛阳政局中爆发。", "luoyang", stage="高中", importance=4, priority=2, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0132",)),
    supp("supp_p494_xiaowen", 494, 20, "reform", "北魏孝文帝迁都洛阳", "494年，北魏孝文帝迁都洛阳，推行汉化改革。", "luoyang", importance=5, priority=1, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0030",), related_people=("北魏孝文帝",)),
    supp("supp_p548_houjing", 548, 20, "war", "侯景之乱", "548年，侯景起兵攻入建康，南朝梁由盛转衰。", "jiankang", stage="高中", importance=4, priority=2, source_pair=TONGJIAN_SOURCES, related_people=("侯景",)),
    supp("supp_p605_canal", 605, 20, "infrastructure", "隋开通济渠", "605年，隋炀帝下令开通济渠，大运河体系开始成形。", "luoyang", importance=5, priority=1, source_pair=TONGJIAN_SOURCES, related_polity_ids=("polity_0158",), related_people=("隋炀帝",)),
    supp("supp_p630_tujue", 630, 20, "war", "唐灭东突厥", "630年，唐军击败东突厥，颉利可汗被俘。", "mobei_orhon", stage="高中", importance=4, priority=2, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059", "polity_0175")),
    supp("supp_p641_wencheng", 641, 20, "diplomacy", "文成公主入藏", "641年，文成公主从长安入藏，唐蕃关系进入新阶段。", "changan", importance=4, priority=2, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059", "polity_0172"), related_people=("文成公主", "松赞干布")),
    supp("supp_p690_wuzhou", 690, 20, "dynasty_start", "武则天称帝", "690年，武则天在洛阳称帝，改国号为周。", "luoyang", importance=4, priority=1, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",), related_people=("武则天",)),
    supp("supp_p751_talas", 751, 20, "war", "怛罗斯之战", "751年，唐军与阿拔斯军在怛罗斯交战，唐军失利。", "talas", stage="高中", importance=4, priority=2, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",)),
    supp("supp_p780_liangshuifa", 780, 20, "institution", "两税法实行", "780年，杨炎主持推行两税法，唐代财政制度发生重要变化。", "changan", stage="高中", importance=5, priority=1, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",), related_people=("杨炎",)),
    supp("supp_p875_huangchao", 875, 20, "war", "黄巢起义爆发", "875年，黄巢起兵响应王仙芝，唐末农民战争扩大。", "heze", importance=4, priority=2, source_pair=TANG_SOURCES, related_polity_ids=("polity_0059",), related_people=("黄巢",)),
    supp("supp_p1043_qingli", 1043, 20, "reform", "庆历新政", "1043年，范仲淹、富弼等在开封推动庆历新政。", "kaifeng", stage="高中", importance=4, priority=2, source_pair=SONG_SOURCES, related_polity_ids=("polity_0026",), related_people=("范仲淹", "富弼")),
    supp("supp_p1069_wanganshi", 1069, 20, "reform", "王安石变法", "1069年，宋神宗任用王安石，在开封推行新法。", "kaifeng", importance=5, priority=1, source_pair=SONG_SOURCES, related_polity_ids=("polity_0026",), related_people=("王安石", "宋神宗")),
    supp("supp_p1141_shaoxing", 1141, 20, "diplomacy", "绍兴和议", "1141年，南宋与金达成绍兴和议，宋金对峙格局固定下来。", "hangzhou_linan", importance=4, priority=2, source_pair=SONG_SOURCES, related_polity_ids=("polity_0034", "polity_0154")),
    supp("supp_p1206_mongol", 1206, 20, "dynasty_start", "铁木真建蒙古国", "1206年，铁木真在斡难河一带被推为成吉思汗，蒙古政权形成。", "onon", stage="高中", importance=5, priority=1, source_pair=SONG_SOURCES, related_people=("铁木真",)),
    supp("supp_p1273_xiangyang", 1273, 20, "war", "襄阳陷落", "1273年，元军攻下襄阳，南宋长江防线被打开。", "xiangyang", importance=5, priority=1, source_pair=SONG_SOURCES, related_polity_ids=("polity_0034", "polity_0013")),
    supp("supp_p1351_redturban", 1351, 20, "war", "红巾军起义", "1351年，刘福通等在颍州起兵，元末红巾军起义爆发。", "yingzhou", importance=4, priority=2, source_pair=("《元史》|中国社会科学出版社《中国历史年表数据库》", "https://ctext.org/yuan-shi/zh|https://www.csspw.com.cn/cpdigitaldetail_15988_2074979.jhtml"), related_polity_ids=("polity_0013",), related_people=("刘福通",)),
    supp("supp_p1405_zhenghe", 1405, 20, "diplomacy", "郑和下西洋", "1405年，郑和船队从刘家港出发，开始第一次下西洋。", "liujia", importance=5, priority=1, source_pair=MING_SOURCES, related_polity_ids=("polity_0072",), related_people=("郑和",)),
    supp("supp_p1421_beijing", 1421, 20, "capital_relocation", "明迁都北京", "1421年，明成祖正式以北京为京师，南京成为留都。", "beijing", importance=4, priority=1, source_pair=MING_SOURCES, related_polity_ids=("polity_0072",), related_people=("明成祖",)),
    supp("supp_p1567_longqing", 1567, 20, "trade", "隆庆开关", "1567年，明朝开放月港民间出海贸易，海禁政策出现松动。", "yuegang", stage="高中", importance=4, priority=2, source_pair=MING_SOURCES, related_polity_ids=("polity_0072",)),
    supp("supp_p1572_zhangjuzheng", 1572, 20, "reform", "张居正改革", "1572年，张居正入主内阁后推行考成法等改革。", "beijing", stage="高中", importance=4, priority=2, source_pair=MING_SOURCES, related_polity_ids=("polity_0072",), related_people=("张居正",)),
    supp("supp_p1581_yitiaobian", 1581, 20, "institution", "一条鞭法推广", "1581年前后，明朝在全国推广一条鞭法，赋役折银征收。", "beijing", stage="高中", importance=4, priority=2, source_pair=MING_SOURCES, related_polity_ids=("polity_0072",), related_people=("张居正",)),
    supp("supp_p1619_sarhu", 1619, 20, "war", "萨尔浒之战", "1619年，努尔哈赤在萨尔浒击败明军，辽东形势逆转。", "sarhu", importance=4, priority=2, source_pair=MING_SOURCES, related_polity_ids=("polity_0072", "polity_0054"), related_people=("努尔哈赤",)),
    supp("supp_p1661_taiwan", 1661, 20, "war", "郑成功攻台", "1661年，郑成功率军登陆台湾，围攻荷兰据点。", "tainan", stage="高中", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("郑成功",)),
    supp("supp_p1673_sanfan", 1673, 20, "war", "三藩之乱爆发", "1673年，吴三桂在云南起兵，三藩之乱爆发。", "kunming", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("吴三桂",)),
    supp("supp_p1689_nerchinsk", 1689, 20, "diplomacy", "尼布楚条约", "1689年，清朝与俄国在尼布楚订约，划定东北边界。", "nerchinsk", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1839_humen", 1839, 20, "event", "虎门销烟", "1839年，林则徐在虎门集中销毁鸦片。", "humen", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("林则徐",)),
    supp("supp_p1842_nanjing", 1842, 20, "treaty", "《南京条约》签订", "1842年，清政府在南京附近与英国签订《南京条约》。", "jianye", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1856_second_opium", 1856, 20, "war", "第二次鸦片战争爆发", "1856年，英法借口广州事件扩大对清战争，第二次鸦片战争爆发。", "guangzhou", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1861_yangwu", 1861, 20, "institution", "总理衙门设立", "1861年，清廷在北京设立总理衙门，洋务运动由此展开。", "beijing", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1864_taiping_end", 1864, 20, "war", "天京陷落", "1864年，湘军攻入天京，太平天国失败。", "jianye", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("曾国藩",)),
    supp("supp_p1884_xinjiang", 1884, 20, "institution", "新疆建省", "1884年，清廷设新疆省，以迪化为省会。", "urumqi", importance=4, priority=2, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1894_jiawu", 1894, 20, "war", "甲午战争爆发", "1894年，中日舰队在丰岛海域交火，甲午战争爆发。", "asan_pungdo", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1895_shimonoseki", 1895, 20, "treaty", "《马关条约》签订", "1895年，李鸿章在马关与日本签订《马关条约》。", "shimonoseki", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("李鸿章",)),
    supp("supp_p1898_wuxu", 1898, 20, "reform", "戊戌变法", "1898年，光绪帝在北京推行维新变法，百日后失败。", "beijing", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",), related_people=("光绪帝", "康有为", "梁启超")),
    supp("supp_p1901_xinchou", 1901, 20, "treaty", "《辛丑条约》签订", "1901年，清政府在北京与列强签订《辛丑条约》。", "beijing", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1905_exam", 1905, 20, "institution", "废除科举", "1905年，清廷下诏停止科举考试，延续千年的取士制度结束。", "beijing", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
    supp("supp_p1911_republic", 1911, 30, "event", "各省响应辛亥革命", "1911年，武昌起义后，多省宣布脱离清廷。", "wuchang", importance=5, priority=1, source_pair=QING_SOURCES, related_polity_ids=("polity_0096",)),
]

SUPPLEMENTAL_EVENT_SPECS.extend([
    supp("supp_p1912_republic_founded", 1912, 10, "dynasty_start", "中华民国临时政府成立", "1912年1月1日，孙中山在南京就任临时大总统，中华民国临时政府成立。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0183",), related_people=("孙中山",)),
    supp("supp_p1912_qing_abdication", 1912, 15, "dynasty_end", "清帝退位", "1912年2月，清帝退位，帝制结束，中华民国北京政府承接全国名义中央地位。", "beijing", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0096", "polity_0184"), related_people=("袁世凯",)),
    supp("supp_p1912_yuan_beijing", 1912, 20, "capital_relocation", "临时政府政治中心转北京", "1912年袁世凯就任临时大总统后，中华民国中央政治中心由南京转往北京。", "beijing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0183", "polity_0184"), related_people=("袁世凯",)),
    supp("supp_p1912_tibet_kashag", 1912, 35, "event", "西藏噶厦事实自治延续", "清朝驻藏机构瓦解后，拉萨噶厦维持事实自治，中华民国中央政府仅保留法理主张。", "lhasa", stage="高中", importance=4, priority=3, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0187", "polity_0210")),
    supp("supp_p1913_second_revolution", 1913, 20, "war", "二次革命", "1913年，国民党人与南方部分省份反袁失败，袁世凯进一步集中北京政府权力。", "nanjing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184",)),
    supp("supp_p1914_qingdao_occupation", 1914, 20, "occupation", "日本占领青岛胶澳", "1914年，日本在第一次世界大战中攻占德国胶澳租借地，青岛转入日本占领。", "qingdao", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0201",)),
    supp("supp_p1915_twenty_one_demands", 1915, 15, "treaty", "二十一条交涉", "1915年，日本向北京政府提出二十一条要求，山东、南满和内蒙古权益问题加剧主权危机。", "beijing", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184",)),
    supp("supp_p1915_yuan_monarchy", 1915, 30, "event", "袁世凯称帝筹备", "1915年底，袁世凯推动帝制，激起护国战争和国内强烈反对。", "beijing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184",), related_people=("袁世凯",)),
    supp("supp_p1916_national_protection", 1916, 10, "war", "护国战争与帝制取消", "1916年，护国战争迫使袁世凯取消帝制，北京政府进入军阀政治阶段。", "kunming", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0185"), related_people=("袁世凯", "蔡锷")),
    supp("supp_p1916_yuan_death", 1916, 30, "event", "袁世凯去世", "1916年袁世凯去世后，北洋体系分裂为多个军阀派系，中央名义与地方实控进一步分离。", "beijing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0185"), related_people=("袁世凯",)),
    supp("supp_p1917_zhangxun_restoration", 1917, 15, "event", "张勋复辟失败", "1917年，张勋拥清帝短暂复辟，旋即失败，北京政府的共和制度危机暴露无遗。", "beijing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184",)),
    supp("supp_p1917_constitutional_protection", 1917, 25, "event", "护法军政府在广州成立", "1917年，孙中山等在广州组织护法军政府，南北政权对立格局形成。", "guangzhou", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0186"), related_people=("孙中山",)),
    supp("supp_p1919_may_fourth", 1919, 20, "event", "五四运动", "1919年，北京学生因巴黎和会山东问题爆发示威，五四运动推动新文化和民族主义浪潮。", "beijing", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184",)),
    supp("supp_p1920_zhili_anhui", 1920, 20, "war", "直皖战争", "1920年，直系、奉系击败皖系，北洋军阀内部权力格局重组。", "beijing", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0185",)),
    supp("supp_p1921_ccp_founded", 1921, 20, "event", "中国共产党成立", "1921年，中国共产党第一次全国代表大会在上海召开，随后转至嘉兴南湖完成会议。", "shanghai", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0184", "polity_0202", "polity_0203")),
    supp("supp_p1921_outer_mongolia_revolution", 1921, 35, "event", "外蒙古革命政权确立", "1921年，外蒙古革命力量在苏俄支持下进入库伦，外蒙古事实独立地位进一步巩固。", "ulaanbaatar", stage="高中", importance=4, priority=3, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0209",)),
    supp("supp_p1922_first_zhili_fengtian", 1922, 10, "war", "第一次直奉战争", "1922年，直系击败奉系，控制北京政府，北洋派系格局再次变化。", "beijing", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0185")),
    supp("supp_p1922_qingdao_return", 1922, 25, "retrocession", "青岛胶澳归还中国", "1922年，青岛及胶澳租借地行政权归还中国，日本占领胶澳青岛阶段结束。", "qingdao", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0184", "polity_0201")),
    supp("supp_p1923_sun_joffe", 1923, 20, "diplomacy", "孙文越飞宣言", "1923年，孙中山与苏联代表越飞发表宣言，国民党改组和第一次国共合作的外部条件成熟。", "shanghai", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0186",), related_people=("孙中山",)),
    supp("supp_p1924_first_united_front", 1924, 10, "institution", "第一次国共合作形成", "1924年，国民党一大在广州召开，联俄、联共、扶助农工政策确立。", "guangzhou", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0186",)),
    supp("supp_p1924_whampoa", 1924, 20, "institution", "黄埔军校创办", "1924年，黄埔军校在广州创办，为国民革命培养军事骨干。", "guangzhou", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0186",)),
    supp("supp_p1924_mongolian_peoples_republic", 1924, 35, "dynasty_start", "蒙古人民共和国成立", "1924年，外蒙古建立蒙古人民共和国，进一步脱离中国中央政府实际控制。", "ulaanbaatar", stage="高中", importance=4, priority=3, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0209",)),
    supp("supp_p1925_may_thirtieth", 1925, 10, "event", "五卅运动", "1925年，上海五卅惨案引发全国性反帝运动，租界和外国势力问题成为政治焦点。", "shanghai", importance=5, priority=1, source_pair=REPUBLIC_LEASE_SOURCES, related_polity_ids=("polity_0202", "polity_0203", "polity_0187")),
    supp("supp_p1925_national_government_guangzhou", 1925, 20, "dynasty_start", "广州国民政府成立", "1925年，国民政府在广州成立，国民革命从地方政权走向全国政治军事行动。", "guangzhou", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187",)),
    supp("supp_p1926_northern_expedition", 1926, 20, "war", "北伐开始", "1926年，国民革命军从广东出师北伐，目标是打倒北洋军阀并统一全国。", "guangzhou", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0185", "polity_0187")),
    supp("supp_p1927_shanghai_purge", 1927, 10, "event", "四一二清党", "1927年，蒋介石在上海发动清党，第一次国共合作破裂，国共内战的长期结构形成。", "shanghai", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187",), related_people=("蒋介石",)),
    supp("supp_p1927_wuhan_nanjing_split", 1927, 15, "event", "宁汉分裂与合流", "1927年，武汉国民政府与南京国民政府一度分裂，随后国民党内部重组。", "wuhan", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187",)),
    supp("supp_p1927_nanchang_uprising", 1927, 20, "war", "南昌起义", "1927年8月，南昌起义爆发，中共开始独立领导武装力量。", "nanchang", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187",)),
    supp("supp_p1927_autumn_harvest", 1927, 30, "war", "秋收起义", "1927年，湘赣边秋收起义后，中共武装转向农村根据地道路。", "changsha", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187",)),
    supp("supp_p1928_jinan_incident", 1928, 10, "war", "济南惨案", "1928年北伐进入山东时，中日军队在济南冲突，日本出兵造成严重伤亡。", "jinan", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1928_northeast_flag", 1928, 25, "diplomacy", "东北易帜", "1928年底，张学良宣布东北易帜，南京国民政府取得全国名义统一。", "shenyang", importance=5, priority=1, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188"), related_people=("张学良",)),
    supp("supp_p1929_cer_conflict", 1929, 20, "war", "中东路事件", "1929年，中苏围绕中东铁路爆发冲突，东北边疆与苏联关系紧张。", "harbin", stage="高中", importance=3, priority=4, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1930_central_plains_war", 1930, 10, "war", "中原大战", "1930年，国民政府与冯玉祥、阎锡山、桂系等地方实力派爆发大规模内战。", "henan_region", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1930_weihai_return", 1930, 25, "retrocession", "威海卫归还中国", "1930年，英国将威海卫归还中国，英租威海卫阶段结束。", "weihai", importance=4, priority=2, source_pair=REPUBLIC_LEASE_SOURCES, related_polity_ids=("polity_0187", "polity_0199")),
    supp("supp_p1931_mukden", 1931, 10, "occupation", "九一八事变", "1931年，日本关东军制造九一八事变并迅速占领东北，东北实控格局剧变。", "shenyang", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1931_chinese_soviet", 1931, 20, "dynasty_start", "中华苏维埃共和国成立", "1931年，中华苏维埃共和国临时中央政府在江西瑞金成立。", "ruijin", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0189",)),
    supp("supp_p1932_manchukuo", 1932, 10, "dynasty_start", "满洲国成立", "1932年，日本扶植满洲国在长春成立，东北进入傀儡政权统治层。", "changchun", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0192",)),
    supp("supp_p1932_shanghai_incident", 1932, 20, "war", "一二八淞沪抗战", "1932年，上海一二八事变爆发，中国军队与日军在上海激战。", "shanghai", importance=4, priority=2, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1933_tanggu_truce", 1933, 15, "treaty", "塘沽协定", "1933年，中日签订塘沽协定，华北局势进入更深的危机。", "tianjin", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0192")),
    supp("supp_p1933_fujian_government", 1933, 30, "event", "福建事变", "1933年，福建人民政府短暂成立，反映南京国民政府内部和地方政治的不稳定。", "fuzhou", importance=3, priority=4, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1934_long_march", 1934, 20, "war", "中央红军开始长征", "1934年，第五次反围剿失败后，中央红军从瑞金等地开始战略转移。", "ruijin", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0189",)),
    supp("supp_p1935_zunyi", 1935, 10, "event", "遵义会议", "1935年，长征途中召开遵义会议，中共领导格局发生重要变化。", "zunyi", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0189",)),
    supp("supp_p1935_luding", 1935, 20, "war", "强渡大渡河与飞夺泸定桥", "1935年，红军在大渡河、泸定桥一线突破封锁，长征继续向西北推进。", "luding", importance=4, priority=3, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0189",)),
    supp("supp_p1935_north_china_crisis", 1935, 30, "occupation", "华北自治危机", "1935年前后，日本推动华北特殊化，北平、天津及河北一带主权压力加剧。", "beijing", stage="高中", importance=4, priority=2, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1935_december_ninth", 1935, 35, "event", "一二九运动", "1935年，北平学生举行抗日救亡示威，要求停止内战、一致抗日。", "beijing", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1936_xian_incident", 1936, 20, "event", "西安事变", "1936年，张学良、杨虎城扣留蒋介石，促成停止内战、共同抗日的政治转向。", "xian", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0189"), related_people=("张学良", "杨虎城", "蒋介石")),
    supp("supp_p1936_suiyuan", 1936, 35, "war", "绥远抗战", "1936年，中国军队在绥远抵御日伪支持的进攻，华北边疆抗日情绪上升。", "zhangjiakou", importance=3, priority=4, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1937_marco_polo", 1937, 10, "war", "卢沟桥事变", "1937年7月，卢沟桥事变爆发，全面抗战开始。", "lugouqiao", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1937_second_united_front", 1937, 15, "diplomacy", "第二次国共合作形成", "1937年全面抗战爆发后，国共两党建立抗日民族统一战线。", "xian", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0190")),
    supp("supp_p1937_shanghai_battle", 1937, 20, "war", "淞沪会战", "1937年，淞沪会战持续数月，上海及周边成为中日主力战场。", "shanghai", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1937_nanjing_fall", 1937, 30, "occupation", "南京陷落", "1937年12月，日军攻占南京，南京国民政府战时迁往重庆。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1937_chongqing_wartime_capital", 1937, 40, "capital_relocation", "重庆成为战时首都", "1937年后，重庆成为国民政府战时政治中心，国统区重心转向西南。", "chongqing", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1938_taierzhuang", 1938, 10, "war", "台儿庄战役", "1938年，台儿庄战役取得重大胜利，鼓舞全国抗战士气。", "taierzhuang", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1938_yellow_river_flood", 1938, 18, "event", "花园口决堤", "1938年，国民政府为迟滞日军在黄河花园口决堤，造成严重民生灾难和区域变迁。", "henan_region", stage="高中", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1938_wuhan_fall", 1938, 25, "occupation", "武汉会战与武汉失守", "1938年，武汉会战后武汉失守，抗战进入更长期的相持阶段。", "wuhan", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1938_guangzhou_fall", 1938, 35, "occupation", "广州沦陷", "1938年，日军攻占广州，华南沿海交通与国统区外援通道受到冲击。", "guangzhou", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1939_changsha", 1939, 15, "war", "第一次长沙会战", "1939年，中国军队在长沙一线阻击日军，华中战场进入反复拉锯。", "changsha", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1939_mengjiang", 1939, 25, "dynasty_start", "蒙疆联合自治政府成立", "1939年，蒙疆联合自治政府在张家口成立，纳入日本华北占领体系。", "zhangjiakou", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0196",)),
    supp("supp_p1940_wang_puppet", 1940, 10, "dynasty_start", "汪精卫南京国民政府成立", "1940年，汪精卫在南京建立日本扶植的改组国民政府。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0195",), related_people=("汪精卫",)),
    supp("supp_p1940_hundred_regiments", 1940, 25, "war", "百团大战", "1940年，八路军在华北发动百团大战，打击日军交通线和据点。", "shanxi_region", importance=4, priority=2, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0190",)),
    supp("supp_p1941_new_fourth_army", 1941, 10, "war", "皖南事变", "1941年，皖南事变造成国共关系严重恶化，但抗日统一战线名义仍维持。", "anhui_region", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188", "polity_0190")),
    supp("supp_p1941_hongkong_fall", 1941, 20, "occupation", "香港沦陷", "1941年12月，香港在太平洋战争爆发后被日军占领，英属香港战前管治中断。", "hongkong", importance=5, priority=1, source_pair=REPUBLIC_LEASE_SOURCES, related_polity_ids=("polity_0205", "polity_0206")),
    supp("supp_p1941_pacific_war", 1941, 30, "war", "太平洋战争爆发", "1941年太平洋战争爆发后，中国战场正式纳入盟国共同战争格局。", "hongkong", importance=4, priority=2, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1942_burma_road", 1942, 20, "war", "滇缅通道危机", "1942年，缅甸战局恶化，滇缅公路和西南国统区外援通道受到严重影响。", "kunming", importance=4, priority=3, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1942_yanan_rectification", 1942, 30, "reform", "延安整风开始", "1942年，中共在延安开展整风运动，边区政治与组织形态发生变化。", "yanan", importance=4, priority=3, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0190",)),
    supp("supp_p1943_unequal_treaties", 1943, 10, "treaty", "中美中英新约签订", "1943年，中美、中英签订新约，英美放弃在华治外法权，上海公共租界等旧特权体系走向终结。", "chongqing", importance=5, priority=1, source_pair=REPUBLIC_LEASE_SOURCES, related_polity_ids=("polity_0187", "polity_0202", "polity_0204")),
    supp("supp_p1943_cairo", 1943, 20, "diplomacy", "开罗宣言", "1943年，开罗宣言提出日本应归还中国东北、台湾、澎湖等地，成为战后接收的重要文本依据。", "cairo", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_TREATY_SOURCES, related_polity_ids=("polity_0187", "polity_0197")),
    supp("supp_p1944_ichigo", 1944, 10, "war", "豫湘桂战役", "1944年，日军发动豫湘桂战役，贯通大陆交通线，国统区受到严重冲击。", "hengyang", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0188", "polity_0195")),
    supp("supp_p1944_three_districts", 1944, 25, "dynasty_start", "新疆三区革命爆发", "1944年，新疆伊犁、塔城、阿山三区形成反国民政府地方政权。", "yili", importance=4, priority=3, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0211", "polity_0212")),
    supp("supp_p1945_soviet_manchuria", 1945, 10, "occupation", "苏军进入东北", "1945年8月，苏联对日宣战后进入东北，满洲国迅速瓦解，东北接收与争夺随即展开。", "shenyang", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0192", "polity_0187", "polity_0191")),
    supp("supp_p1945_japan_surrender", 1945, 15, "war", "日本投降", "1945年，日本投降，中国抗日战争结束，日占区、傀儡政权和殖民管治区进入接收阶段。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_TREATY_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0195")),
    supp("supp_p1945_taiwan_retrocession", 1945, 20, "retrocession", "台湾澎湖接收", "1945年10月，中华民国接收台湾、澎湖，日本台湾总督府统治结束。", "taipei", importance=5, priority=1, source_pair=REPUBLIC_TREATY_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0197")),
    supp("supp_p1945_guangzhouwan_return", 1945, 25, "retrocession", "广州湾归还中国", "1945年，法租广州湾归还中国，改设湛江市。", "zhanjiang", importance=4, priority=2, source_pair=REPUBLIC_LEASE_SOURCES, related_polity_ids=("polity_0187", "polity_0200")),
    supp("supp_p1945_manchukuo_end", 1945, 30, "dynasty_end", "满洲国结束", "1945年，日本战败和苏军进入东北后，满洲国政权结束。", "changchun", importance=5, priority=1, source_pair=REPUBLIC_WAR_JAPAN_SOURCES, related_polity_ids=("polity_0192",)),
    supp("supp_p1945_outer_mongolia_referendum", 1945, 35, "diplomacy", "外蒙古独立公投", "1945年，外蒙古举行独立公投，中华民国政府随后承认其独立。", "ulaanbaatar", stage="高中", importance=5, priority=1, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0209", "polity_0187")),
    supp("supp_p1945_chongqing_talks", 1945, 45, "diplomacy", "重庆谈判", "1945年，国共两党在重庆谈判，试图避免战后全面内战。", "chongqing", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0191"), related_people=("蒋介石", "毛泽东")),
    supp("supp_p1946_pcc", 1946, 10, "diplomacy", "政治协商会议召开", "1946年，政治协商会议试图重建战后政治秩序，但国共军事冲突迅速扩大。", "chongqing", importance=4, priority=3, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0191")),
    supp("supp_p1946_nanjing_capital_return", 1946, 20, "capital_relocation", "国民政府还都南京", "1946年，国民政府由重庆还都南京，战时陪都阶段结束。", "nanjing", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1946_civil_war_full", 1946, 30, "civil_war_control", "全面内战爆发", "1946年，国共大规模军事冲突全面展开，东北、中原、华北成为主要争夺区域。", "henan_region", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1946_outer_mongolia_recognition", 1946, 40, "diplomacy", "中华民国承认外蒙古独立", "1946年，中华民国政府承认外蒙古独立，名义疆域与实际国际边界出现重大调整。", "ulaanbaatar", importance=5, priority=1, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0187", "polity_0209")),
    supp("supp_p1947_taiwan_228", 1947, 10, "event", "台湾二二八事件", "1947年，台湾发生二二八事件，战后接收治理与地方社会关系急剧恶化。", "taipei", importance=4, priority=2, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0188",)),
    supp("supp_p1947_yanan_captured", 1947, 20, "civil_war_control", "国军占领延安", "1947年，国民政府军占领延安，中共中央转入陕北机动作战。", "yanan", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1947_dabie", 1947, 30, "civil_war_control", "刘邓大军挺进大别山", "1947年，刘伯承、邓小平率部挺进大别山，解放区战略态势由防御转向进攻。", "hubei_region", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191"), related_people=("刘伯承", "邓小平")),
    supp("supp_p1947_constitution", 1947, 40, "institution", "中华民国宪法施行", "1947年，《中华民国宪法》施行，国民政府进入行宪体制，但内战仍在扩大。", "nanjing", importance=4, priority=3, source_pair=REPUBLIC_SOURCES, related_polity_ids=("polity_0187",)),
    supp("supp_p1948_liaoshen_start", 1948, 10, "war", "辽沈战役开始", "1948年，辽沈战役在东北展开，锦州成为决定东北战局的关键。", "jinzhou", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1948_jinzhou_taken", 1948, 18, "civil_war_control", "锦州易手", "1948年，解放军攻占锦州，东北国民政府军战略退路被切断。", "jinzhou", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1948_huaihai", 1948, 25, "war", "淮海战役开始", "1948年，淮海战役在徐州及周边展开，华东、中原战局进入决战。", "xuzhou", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1948_pingjin", 1948, 35, "war", "平津战役开始", "1948年底，平津战役展开，华北控制权即将发生决定性转移。", "beijing", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_beiping_peace", 1949, 10, "civil_war_control", "北平和平易手", "1949年1月，北平和平解放，平津战役结束，华北控制格局改变。", "beijing", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_yangtze_crossing", 1949, 20, "war", "渡江战役", "1949年4月，解放军发起渡江战役，长江防线被突破。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_nanjing_taken", 1949, 25, "civil_war_control", "南京易手", "1949年4月，南京被解放军占领，国民政府大陆中央统治象征性终结。", "nanjing", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0188", "polity_0191")),
    supp("supp_p1949_shanghai_taken", 1949, 30, "civil_war_control", "上海易手", "1949年5月，上海被解放军占领，长江下游和最大城市控制权转移。", "shanghai", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_prc_founded", 1949, 40, "dynasty_start", "中华人民共和国成立", "1949年10月1日，中华人民共和国中央人民政府在北京成立。", "beijing", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0213", "polity_0191")),
    supp("supp_p1949_guangzhou_taken", 1949, 45, "civil_war_control", "广州易手", "1949年10月，广州被解放军占领，国民政府南迁重庆等地。", "guangzhou", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_xinjiang_peaceful", 1949, 50, "civil_war_control", "新疆和平解放", "1949年，新疆省政府和三区方面进入和平解放进程，新疆控制关系转入中华人民共和国体系。", "urumqi", importance=4, priority=2, source_pair=REPUBLIC_BORDER_SOURCES, related_polity_ids=("polity_0211", "polity_0212", "polity_0213")),
    supp("supp_p1949_roc_taipei", 1949, 55, "capital_relocation", "中华民国政府迁台", "1949年12月，中华民国中央政府迁往台北，国共内战形成海峡两岸分治格局。", "taipei", importance=5, priority=1, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0187", "polity_0188")),
    supp("supp_p1949_chongqing_taken", 1949, 60, "civil_war_control", "重庆易手", "1949年11月，重庆被解放军占领，国民政府西南据点继续收缩。", "chongqing", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
    supp("supp_p1949_chengdu_taken", 1949, 65, "civil_war_control", "成都易手", "1949年12月，成都战役后西南主要城市控制权转移。", "chengdu", importance=4, priority=2, source_pair=REPUBLIC_CIVIL_WAR_SOURCES, related_polity_ids=("polity_0188", "polity_0191")),
])


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        return [
            {(key or "").lstrip("\ufeff"): (value or "") for key, value in row.items()}
            for row in reader
        ]


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=FIELDNAMES, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in FIELDNAMES})


def clean(value: Any) -> str:
    return str(value or "").strip()


def parse_int(value: Any, default: int | None = None) -> int | None:
    text = clean(value)
    if not text:
        return default
    try:
        return int(float(text))
    except ValueError:
        return default


def year_label(year: int) -> str:
    return f"前{abs(year)}年" if year < 0 else f"{year}年"


def year_key(year: int) -> str:
    return f"m{abs(year)}" if year < 0 else f"p{year}"


def split_pipe(value: str) -> list[str]:
    return [item.strip() for item in clean(value).split("|") if item.strip()]


def normalize_polity_ids(value: str) -> list[str]:
    return [LEGACY_POLITY_ID_MAP.get(item, item) for item in split_pipe(value)]


def join_unique(values: list[str], limit: int | None = None) -> str:
    result: list[str] = []
    for value in values:
        value = clean(value)
        if value and value not in result:
            result.append(value)
        if limit is not None and len(result) >= limit:
            break
    return "|".join(result)


def ensure_dual_sources(source_titles: str, source_urls: str) -> tuple[str, str]:
    titles = split_pipe(source_titles)
    urls = split_pipe(source_urls)
    fallback_pairs = [
        (TIMELINE_SOURCE_TITLE, TIMELINE_SOURCE_URL),
        (CTEXT_SOURCE_TITLE, CTEXT_SOURCE_URL),
        ("课程标准参照", COURSE_SOURCE_URLS.split("|")[0]),
    ]
    for title, url in fallback_pairs:
        if len(titles) >= 2 and len(urls) >= 2:
            break
        if title not in titles:
            titles.append(title)
        if url not in urls:
            urls.append(url)
    return join_unique(titles), join_unique(urls)


def ensure_dual_location_sources(source_titles: str, source_urls: str) -> tuple[str, str]:
    titles = split_pipe(source_titles) + split_pipe(LOCATION_SOURCE_TITLES)
    urls = split_pipe(source_urls) + split_pipe(LOCATION_SOURCE_URLS)
    return join_unique(titles), join_unique(urls)


def location_copy(location: dict[str, Any], note_suffix: str = "") -> dict[str, str]:
    note = clean(location.get("location_note"))
    if note_suffix:
        note = f"{note}；{note_suffix}" if note else note_suffix
    return {
        "location_name": clean(location.get("location_name") or location.get("location_modern_name")),
        "longitude": clean(location.get("longitude")),
        "latitude": clean(location.get("latitude")),
        "location_historical_name": clean(location.get("location_historical_name")),
        "location_modern_name": clean(location.get("location_modern_name")),
        "location_modern_admin_id": clean(location.get("location_modern_admin_id")),
        "location_precision": clean(location.get("location_precision")) or "approximate",
        "location_confidence_score": clean(location.get("location_confidence_score")) or "70",
        "location_source_titles": clean(location.get("location_source_titles")) or LOCATION_SOURCE_TITLES,
        "location_source_urls": clean(location.get("location_source_urls")) or LOCATION_SOURCE_URLS,
        "location_note": note,
    }


def location_from_capital(row: dict[str, str], note_suffix: str = "") -> dict[str, str]:
    historical = clean(row.get("capital_name_historical")) or clean(row.get("capital_name_modern"))
    modern = clean(row.get("capital_name_modern")) or historical
    location = {
        "location_name": modern,
        "longitude": clean(row.get("longitude")),
        "latitude": clean(row.get("latitude")),
        "location_historical_name": historical,
        "location_modern_name": modern,
        "location_modern_admin_id": "",
        "location_precision": clean(row.get("location_precision")) or "city",
        "location_confidence_score": clean(row.get("confidence_score")) or "82",
        "location_source_titles": clean(row.get("source_titles")) or LOCATION_SOURCE_TITLES,
        "location_source_urls": clean(row.get("source_urls")) or LOCATION_SOURCE_URLS,
        "location_note": clean(row.get("confidence_note")),
    }
    return location_copy(location, note_suffix)


def location_from_existing(row: dict[str, Any]) -> dict[str, str] | None:
    if not clean(row.get("longitude")) or not clean(row.get("latitude")):
        return None
    name = clean(row.get("location_name")) or clean(row.get("title"))
    if not name:
        return None
    return location_copy(
        {
            "location_name": name,
            "longitude": clean(row.get("longitude")),
            "latitude": clean(row.get("latitude")),
            "location_historical_name": clean(row.get("location_historical_name")) or name,
            "location_modern_name": clean(row.get("location_modern_name")) or name,
            "location_modern_admin_id": clean(row.get("location_modern_admin_id")),
            "location_precision": clean(row.get("location_precision")) or "region",
            "location_confidence_score": clean(row.get("location_confidence_score")) or "72",
            "location_source_titles": clean(row.get("location_source_titles")) or LOCATION_SOURCE_TITLES,
            "location_source_urls": clean(row.get("location_source_urls")) or LOCATION_SOURCE_URLS,
            "location_note": clean(row.get("location_note")) or "沿用人工事件种子坐标，已补齐古今地名字段。",
        }
    )


def location_by_text(*values: str) -> dict[str, str] | None:
    haystack = " ".join(clean(value) for value in values if clean(value))
    if not haystack:
        return None
    candidates: list[tuple[int, str, dict[str, Any]]] = []
    for key, location in LOCATION_GAZETTEER.items():
        aliases = tuple(location.get("aliases") or ()) + (
            clean(location.get("location_historical_name")),
            clean(location.get("location_modern_name")),
        )
        for alias in aliases:
            if alias and alias in haystack:
                candidates.append((len(alias), key, location))
                break
    if not candidates:
        return None
    _, key, location = sorted(candidates, reverse=True)[0]
    return location_copy(location, f"依据文本匹配“{key}”取主发生点。")


def merge_location(row: dict[str, Any], location: dict[str, str]) -> None:
    loc_titles, loc_urls = ensure_dual_location_sources(
        clean(location.get("location_source_titles")),
        clean(location.get("location_source_urls")),
    )
    for field in (
        "location_name",
        "longitude",
        "latitude",
        "location_historical_name",
        "location_modern_name",
        "location_modern_admin_id",
        "location_precision",
        "location_confidence_score",
        "location_source_titles",
        "location_source_urls",
        "location_note",
    ):
        row[field] = clean(location.get(field))
    row["location_source_titles"] = loc_titles
    row["location_source_urls"] = loc_urls


def truncate(value: str, max_chars: int) -> str:
    value = clean(value).replace("\n", " ")
    return value if len(value) <= max_chars else value[: max_chars - 1] + "…"


def display_text(value: str) -> str:
    text = clean(value)
    for source, target in DISPLAY_TEXT_REPLACEMENTS.items():
        text = text.replace(source, target)
    return text


def polity_display_name(row: dict[str, str]) -> str:
    return display_text(clean(row.get("polity_display_name")) or clean(row.get("polity_name")))


def first_pipe_value(value: str, max_chars: int | None = None) -> str:
    text = display_text(split_pipe(value)[0] if split_pipe(value) else value)
    return truncate(text, max_chars) if max_chars else text


def person_display(value: str, max_chars: int | None = None) -> str:
    raw = split_pipe(value)[0] if split_pipe(value) else clean(value)
    text = display_text(PERSON_DISPLAY_OVERRIDES.get(raw, raw))
    if " " in text:
        parts = [part for part in text.split() if part]
        if len(parts) >= 2 and 1 <= len(parts[-1]) <= 5:
            text = parts[-1]
    return truncate(text, max_chars) if max_chars else text


def deterministic_suffix(*parts: str) -> str:
    digest = hashlib.sha1("|".join(parts).encode("utf-8")).hexdigest()
    return digest[:8]


def is_generated_event(row: dict[str, str]) -> bool:
    event_id = clean(row.get("event_id"))
    return event_id.startswith(GENERATED_PREFIXES)


def source_type_for(source_titles: str, fallback: str = "derived_v03") -> str:
    if "《" in source_titles and "》" in source_titles:
        return "primary_source"
    if source_titles:
        return "secondary_reference"
    return fallback


def is_major_polity(row: dict[str, str]) -> bool:
    name = clean(row.get("polity_name"))
    polity_type = clean(row.get("polity_type"))
    if name in MAJOR_POLITY_NAMES:
        return True
    return "王朝" in polity_type and "诸侯" not in polity_type


def stage_for_polity(row: dict[str, str], *, detail: str = "status") -> str:
    if is_major_polity(row):
        return "初中" if detail in {"status", "period"} else "高中"
    if "诸侯" in clean(row.get("polity_type")) and detail in {"status", "period"}:
        return "高中"
    return "大学"


def stage_for_seed(row: dict[str, str]) -> str:
    existing = clean(row.get("primary_education_stage"))
    if existing in EDUCATION_STAGES:
        return existing
    title = clean(row.get("title"))
    description = clean(row.get("description"))
    haystack = f"{title} {description}"
    if any(keyword in haystack for keyword in SCHOOL_EVENT_KEYWORDS):
        return "初中"
    if clean(row.get("event_type")) in {"war", "unification", "dynasty_start", "dynasty_end"}:
        return "高中"
    return "大学"


def education_tags(primary: str, extra: list[str] | None = None) -> str:
    tags = [primary]
    for item in extra or []:
        if item in EDUCATION_STAGES and item not in tags:
            tags.append(item)
    return "|".join(tags)


def curriculum_basis(stage: str, kind: str) -> str:
    if stage == "小学":
        return "小学跨学科历史文化常识；大陆课标启发式分级"
    if stage == "初中":
        return "义务教育历史课程标准（2022年版）中国古代史/中国近代史学习主题；大陆课标启发式分级"
    if stage == "高中":
        return "普通高中历史课程标准（2017年版2020年修订）中外历史纲要与选择性必修相关主题；大陆课标启发式分级"
    return f"{kind}涉及专题史、地方史或史料辨析，超出中学核心叙事；大学/专业史启发式分级"


def base_event_row(
    *,
    event_id: str,
    year: int,
    sort_order: int,
    date_precision: str,
    item_kind: str,
    event_type: str,
    title: str,
    description: str,
    significance: str,
    stage: str,
    importance_level: int,
    display_priority: int,
    related_polity_ids: list[str],
    related_people: list[str] | None = None,
    location_name: str = "",
    longitude: str = "",
    latitude: str = "",
    location_historical_name: str = "",
    location_modern_name: str = "",
    location_modern_admin_id: str = "",
    location_precision: str = "",
    location_confidence_score: int | str | None = "",
    location_source_titles: str = "",
    location_source_urls: str = "",
    location_note: str = "",
    source_titles: str = "",
    source_urls: str = "",
    source_type: str = "",
    confidence_score: int | str | None = "",
    confidence_note: str = "",
    fact_review_status: str = "verified",
    review_note: str = "",
    coverage_role: str = "exact_year_event",
    coverage_start_year: int | str | None = None,
    coverage_end_year: int | str | None = None,
    coverage_group_id: str = "",
) -> dict[str, Any]:
    return {
        "event_id": event_id,
        "year": year,
        "sort_order": sort_order,
        "date_label": year_label(year),
        "date_precision": date_precision,
        "coverage_role": coverage_role,
        "coverage_start_year": coverage_start_year if coverage_start_year is not None else year,
        "coverage_end_year": coverage_end_year if coverage_end_year is not None else year,
        "coverage_group_id": coverage_group_id or event_id,
        "item_kind": item_kind,
        "event_type": event_type,
        "title": title,
        "description": description,
        "significance": significance,
        "primary_education_stage": stage,
        "education_stage_tags": education_tags(stage, ["高中"] if stage == "初中" else None),
        "curriculum_basis": curriculum_basis(stage, item_kind),
        "importance_level": importance_level,
        "display_priority": display_priority,
        "related_polity_ids": join_unique(related_polity_ids),
        "related_people": join_unique(related_people or []),
        "location_name": location_name,
        "longitude": clean(longitude),
        "latitude": clean(latitude),
        "location_historical_name": location_historical_name,
        "location_modern_name": location_modern_name,
        "location_modern_admin_id": location_modern_admin_id,
        "location_precision": location_precision,
        "location_confidence_score": location_confidence_score if location_confidence_score != "" else "",
        "location_source_titles": location_source_titles,
        "location_source_urls": location_source_urls,
        "location_note": location_note,
        "source_titles": source_titles,
        "source_urls": source_urls,
        "source_type": source_type or source_type_for(source_titles),
        "confidence_score": confidence_score if confidence_score != "" else "",
        "confidence_note": confidence_note,
        "fact_review_status": fact_review_status,
        "review_note": review_note,
    }


def normalize_seed_events(raw_events: list[dict[str, str]]) -> list[dict[str, Any]]:
    per_year_counts: dict[int, int] = defaultdict(int)
    seeds: list[dict[str, Any]] = []
    for raw in raw_events:
        if not clean(raw.get("event_id")) or is_generated_event(raw):
            continue
        year = parse_int(raw.get("year"))
        if year is None or year == 0 or year < YEAR_MIN or year > YEAR_MAX:
            continue
        per_year_counts[year] += 1
        sort_order = parse_int(raw.get("sort_order"), per_year_counts[year] * 10)
        item_kind = clean(raw.get("item_kind")) or "core_event"
        if item_kind not in ITEM_KINDS:
            item_kind = "core_event"
        stage = stage_for_seed(raw)
        event_id = clean(raw["event_id"])
        related_ids = SEED_POLITY_ID_OVERRIDES.get(event_id, normalize_polity_ids(raw.get("related_polity_ids", "")))
        source_titles = clean(raw.get("source_titles"))
        source_urls = clean(raw.get("source_urls"))
        confidence = parse_int(raw.get("confidence_score"))
        raw_description = clean(raw.get("description"))
        description = SEED_DESCRIPTION_OVERRIDES.get(event_id, raw_description)
        raw_significance = clean(raw.get("significance"))
        significance = description if not raw_significance or raw_significance == raw_description else raw_significance
        seeds.append(
            base_event_row(
                event_id=event_id,
                year=year,
                sort_order=sort_order or per_year_counts[year] * 10,
                date_precision=clean(raw.get("date_precision")) if clean(raw.get("date_precision")) in DATE_PRECISIONS else "year",
                item_kind=item_kind,
                event_type=clean(raw.get("event_type")) or "event",
                title=clean(raw.get("title")),
                description=description,
                significance=significance,
                stage=stage,
                importance_level=parse_int(raw.get("importance_level"), 5) or 5,
                display_priority=parse_int(raw.get("display_priority"), 1) or 1,
                related_polity_ids=related_ids,
                related_people=split_pipe(raw.get("related_people", "")),
                location_name=clean(raw.get("location_name")),
                longitude=clean(raw.get("longitude")),
                latitude=clean(raw.get("latitude")),
                source_titles=source_titles,
                source_urls=source_urls,
                source_type=clean(raw.get("source_type")) or source_type_for(source_titles),
                confidence_score=confidence if confidence is not None else "",
                confidence_note=clean(raw.get("confidence_note")) or "人工关键事件种子；字段由构建脚本规范化",
            )
        )
    return seeds


def add_supplemental_events(events_by_year: dict[int, list[dict[str, Any]]]) -> None:
    existing_ids = {clean(event.get("event_id")) for events in events_by_year.values() for event in events}
    existing_titles = {
        (parse_int(event.get("year")), clean(event.get("title")))
        for events in events_by_year.values()
        for event in events
    }
    for spec in SUPPLEMENTAL_EVENT_SPECS:
        if spec["event_id"] in existing_ids:
            continue
        if (spec["year"], spec["title"]) in existing_titles:
            continue
        row = base_event_row(
            event_id=spec["event_id"],
            year=spec["year"],
            sort_order=spec["sort_order"],
            date_precision="year",
            item_kind="core_event" if spec["importance_level"] >= 5 else "representative_event",
            event_type=spec["event_type"],
            title=spec["title"],
            description=spec["description"],
            significance=spec["significance"],
            stage=spec["stage"],
            importance_level=spec["importance_level"],
            display_priority=spec["display_priority"],
            related_polity_ids=spec["related_polity_ids"],
            related_people=spec["related_people"],
            source_titles=spec["source_titles"],
            source_urls=spec["source_urls"],
            source_type=source_type_for(spec["source_titles"]),
            confidence_score=88,
            confidence_note="按教材高频与通史年表补充，进入播放流前已补主发生点。",
            review_note="补充关键事件；事实源与地点源分开记录。",
        )
        row["_location_key"] = spec["location_key"]
        events_by_year[spec["year"]].append(row)
        existing_ids.add(spec["event_id"])
        existing_titles.add((spec["year"], spec["title"]))


def polity_rank(row: dict[str, str]) -> tuple[int, int, str]:
    name = clean(row.get("polity_name"))
    score = 0
    if name in MAJOR_POLITY_NAMES:
        score += 200
    polity_type = clean(row.get("polity_type"))
    if "王朝" in polity_type:
        score += 80
    if "政权" in polity_type:
        score += 40
    if "诸侯" in polity_type:
        score += 15
    confidence = parse_int(row.get("confidence_score"), 0) or 0
    score += min(confidence, 100)
    try:
        fallback_year = row.get("year") or 0
        start = int(row.get("polity_start_year") or fallback_year)
        end = int(row.get("polity_end_year") or fallback_year)
        duration = abs(end - start)
    except ValueError:
        duration = 0
    return (-score, -duration, name)


def group_yearly_rows(rows: list[dict[str, str]]) -> dict[int, dict[str, dict[str, Any]]]:
    grouped: dict[int, dict[str, dict[str, Any]]] = defaultdict(dict)
    for row in rows:
        year = parse_int(row.get("year"))
        polity_id = clean(row.get("polity_id"))
        if year is None or year == 0 or not polity_id:
            continue
        bucket = grouped[year].setdefault(
            polity_id,
            {
                "first": row,
                "rulers": [],
            },
        )
        if clean(row.get("ruler_id")):
            bucket["rulers"].append(row)
    return grouped


def read_capitals() -> dict[str, list[dict[str, str]]]:
    capitals: dict[str, list[dict[str, str]]] = defaultdict(list)
    for row in read_csv(CAPITALS_CSV):
        polity_id = clean(row.get("polity_id"))
        if polity_id:
            capitals[polity_id].append(row)
    for rows in capitals.values():
        rows.sort(key=lambda row: parse_int(row.get("valid_from_year"), 0) or 0)
    return capitals


def active_capital(capitals_by_polity: dict[str, list[dict[str, str]]], polity_id: str, year: int) -> dict[str, str] | None:
    for row in capitals_by_polity.get(polity_id, []):
        start = parse_int(row.get("valid_from_year"))
        end = parse_int(row.get("valid_to_year"))
        if start is None or end is None:
            continue
        if start <= year <= end and clean(row.get("is_primary")).lower() == "true":
            return row
    return None


def boundary_capital_for_year(
    capitals_by_polity: dict[str, list[dict[str, str]]],
    polity_id: str,
    year: int,
) -> dict[str, str] | None:
    active = active_capital(capitals_by_polity, polity_id, year)
    if active:
        return active
    rows = capitals_by_polity.get(polity_id, [])
    if not rows:
        return None
    before_or_at = [
        row for row in rows
        if (parse_int(row.get("valid_from_year")) or -999999) <= year
    ]
    if before_or_at:
        return sorted(before_or_at, key=lambda row: parse_int(row.get("valid_from_year"), -999999) or -999999)[-1]
    return rows[0]


def resolve_event_location(
    row: dict[str, Any],
    master_by_id: dict[str, dict[str, str]],
    capitals_by_polity: dict[str, list[dict[str, str]]],
) -> dict[str, str] | None:
    explicit_key = clean(row.get("_location_key")) or EVENT_LOCATION_KEYS.get(clean(row.get("event_id")), "")
    if explicit_key and explicit_key in LOCATION_GAZETTEER:
        return location_copy(LOCATION_GAZETTEER[explicit_key], "人工事件主发生点。")

    existing = location_from_existing(row)
    if existing:
        return existing

    year = parse_int(row.get("year"))
    related_ids = split_pipe(row.get("related_polity_ids", ""))
    if year is not None:
        for polity_id in related_ids:
            capital = boundary_capital_for_year(capitals_by_polity, polity_id, year)
            if capital and clean(capital.get("longitude")) and clean(capital.get("latitude")):
                return location_from_capital(capital, "政权起灭事件以该政权都城/主中心落点。")

    for polity_id in related_ids:
        polity = master_by_id.get(polity_id)
        if not polity:
            continue
        key = POLITY_LOCATION_KEYS.get(clean(polity.get("polity_name")))
        if key and key in LOCATION_GAZETTEER:
            return location_copy(LOCATION_GAZETTEER[key], "政权起灭事件以主都城或核心区域落点。")
        matched = location_by_text(
            polity.get("capital_historical", ""),
            polity.get("capital_modern", ""),
            polity.get("modern_admin_units_raw", ""),
            polity.get("historical_geography_raw", ""),
        )
        if matched:
            return matched

    return location_by_text(
        clean(row.get("location_name")),
        clean(row.get("title")),
        clean(row.get("description")),
        clean(row.get("significance")),
    )


def enriched_verified_events(events: list[dict[str, Any]]) -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    master_rows = read_csv(MASTER_CSV)
    master_by_id = {clean(row.get("polity_id")): row for row in master_rows if clean(row.get("polity_id"))}
    capitals_by_polity = read_capitals()
    verified: list[dict[str, Any]] = []
    review_rows: list[dict[str, Any]] = []
    seen_ids: set[str] = set()

    for event in events:
        row = dict(event)
        event_id = clean(row.get("event_id"))
        if not event_id or event_id in seen_ids:
            review_rows.append(
                {
                    "event_id": event_id,
                    "year": clean(row.get("year")),
                    "title": clean(row.get("title")),
                    "event_type": clean(row.get("event_type")),
                    "reason": "duplicate_or_empty_event_id",
                    "source_titles": clean(row.get("source_titles")),
                    "review_note": "事件 ID 为空或重复，未进入正式播放流。",
                }
            )
            continue
        seen_ids.add(event_id)

        source_titles, source_urls = ensure_dual_sources(clean(row.get("source_titles")), clean(row.get("source_urls")))
        row["source_titles"] = source_titles
        row["source_urls"] = source_urls
        row["source_type"] = clean(row.get("source_type")) or source_type_for(source_titles)
        row["confidence_score"] = clean(row.get("confidence_score")) or "80"
        row["coverage_role"] = clean(row.get("coverage_role")) or "exact_year_event"
        row["coverage_start_year"] = clean(row.get("coverage_start_year")) or clean(row.get("year"))
        row["coverage_end_year"] = clean(row.get("coverage_end_year")) or clean(row.get("year"))
        row["coverage_group_id"] = clean(row.get("coverage_group_id")) or event_id

        location = resolve_event_location(row, master_by_id, capitals_by_polity)
        if not location or not clean(location.get("longitude")) or not clean(location.get("latitude")):
            row["fact_review_status"] = "needs_review"
            review_rows.append(
                {
                    "event_id": event_id,
                    "year": clean(row.get("year")),
                    "title": clean(row.get("title")),
                    "event_type": clean(row.get("event_type")),
                    "reason": "missing_reliable_location",
                    "source_titles": source_titles,
                    "review_note": "尚未找到可追溯主发生点，暂不进入播放事件流。",
                }
            )
            continue

        merge_location(row, location)
        row["fact_review_status"] = "verified"
        loc_note = clean(row.get("location_note"))
        row["review_note"] = clean(row.get("review_note")) or f"事实与地点已进入脚本复核；{loc_note or '主发生点可用于地图播放。'}"
        verified.append(row)

    return verified, review_rows


def all_playable_years() -> list[int]:
    return [year for year in range(YEAR_MIN, YEAR_MAX + 1) if year != 0]


def anchor_for_year(year: int) -> dict[str, Any]:
    for spec in RANGE_ANCHOR_SPECS:
        if spec["start_year"] <= year <= spec["end_year"]:
            return spec
    raise ValueError(f"no range anchor covers {year}")


def add_range_anchor_coverage(events: list[dict[str, Any]]) -> list[dict[str, Any]]:
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in events:
        year = parse_int(row.get("year"))
        if year is not None:
            by_year[year].append(row)

    covered = set(by_year)
    filled = list(events)
    for year in all_playable_years():
        if year in covered:
            continue
        spec = anchor_for_year(year)
        location = location_copy(
            LOCATION_GAZETTEER[spec["location_key"]],
            f"范围锚点覆盖{year_label(spec['start_year'])}至{year_label(spec['end_year'])}，用于补足本年历史进程。",
        )
        source_titles, source_urls = ensure_dual_sources(spec["source_titles"], spec["source_urls"])
        row = base_event_row(
            event_id=f"range_{year_key(year)}_{spec['anchor_id']}",
            year=year,
            sort_order=9000,
            date_precision="range",
            item_kind="range_anchor",
            event_type=spec["event_type"],
            title=spec["title"],
            description=spec["description"],
            significance=spec["description"],
            stage=spec["stage"],
            importance_level=spec["importance_level"],
            display_priority=spec["display_priority"],
            related_polity_ids=spec["related_polity_ids"],
            related_people=[],
            source_titles=source_titles,
            source_urls=source_urls,
            source_type=source_type_for(source_titles),
            confidence_score=82,
            confidence_note="范围锚点来自权威断代与年表来源；用于说明本年所处历史进程，不等同于本年突发事件。",
            review_note="verified range_anchor；确无更高优先级 exact-year 事件时用于播放覆盖。",
            coverage_role="range_anchor",
            coverage_start_year=spec["start_year"],
            coverage_end_year=spec["end_year"],
            coverage_group_id=f"range_anchor:{spec['anchor_id']}",
        )
        row["date_label"] = f"{year_label(spec['start_year'])}至{year_label(spec['end_year'])}"
        merge_location(row, location)
        row["fact_review_status"] = "verified"
        filled.append(row)
        covered.add(year)

    return sorted(
        filled,
        key=lambda event: (
            int(event["year"]),
            parse_int(event.get("sort_order"), 9999) or 9999,
            clean(event.get("event_id")),
        ),
    )


def write_review_report(path: Path, rows: list[dict[str, Any]]) -> None:
    fieldnames = ["event_id", "year", "title", "event_type", "reason", "source_titles", "review_note"]
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, extrasaction="ignore", lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow({field: row.get(field, "") for field in fieldnames})


def write_coverage_report(path: Path, events: list[dict[str, Any]]) -> None:
    fieldnames = [
        "year",
        "year_label",
        "event_count",
        "best_coverage_role",
        "has_exact_year_event",
        "used_range_anchor",
        "top_event_id",
        "top_event_title",
        "source_url_min_count",
        "min_location_confidence_score",
    ]
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for row in events:
        year = parse_int(row.get("year"))
        if year is not None:
            by_year[year].append(row)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for year in all_playable_years():
            rows = sorted(
                by_year.get(year, []),
                key=lambda row: (
                    parse_int(row.get("display_priority"), 5) or 5,
                    -(parse_int(row.get("importance_level"), 0) or 0),
                    parse_int(row.get("sort_order"), 9999) or 9999,
                ),
            )
            top = rows[0] if rows else {}
            writer.writerow(
                {
                    "year": year,
                    "year_label": year_label(year),
                    "event_count": len(rows),
                    "best_coverage_role": clean(top.get("coverage_role")),
                    "has_exact_year_event": any(clean(row.get("coverage_role")) == "exact_year_event" for row in rows),
                    "used_range_anchor": any(clean(row.get("coverage_role")) == "range_anchor" for row in rows),
                    "top_event_id": clean(top.get("event_id")),
                    "top_event_title": clean(top.get("title")),
                    "source_url_min_count": min((len(split_pipe(row.get("source_urls", ""))) for row in rows), default=0),
                    "min_location_confidence_score": min((parse_int(row.get("location_confidence_score"), 0) or 0 for row in rows), default=0),
                }
            )


def boundary_precision(row: dict[str, str]) -> str:
    precision = clean(row.get("polity_date_precision"))
    if precision in DATE_PRECISIONS:
        return precision
    text = " ".join(
        [
            clean(row.get("polity_start_label")),
            clean(row.get("polity_end_label")),
            clean(row.get("polity_date_raw")),
            clean(row.get("confidence_note")),
        ]
    )
    if any(marker in text for marker in ("约", "前后", "失考", "争议", "不详")):
        return "approx"
    return "year"


def is_transition_successor(value: str) -> bool:
    return any(marker in clean(value) for marker in ("转为", "改称", "改组为", "继承为"))


def boundary_title(row: dict[str, str], boundary_kind: str) -> str:
    name = polity_display_name(row)
    if boundary_kind == "start":
        return f"{name}建立" if is_major_polity(row) else f"{name}建国"
    successor = first_pipe_value(row.get("destroyed_by_or_successor", ""), 28)
    if is_transition_successor(successor):
        return f"{name}{successor}"
    return f"{name}灭亡"


def boundary_description(row: dict[str, str], boundary_kind: str, year: int) -> str:
    name = polity_display_name(row)
    date = year_label(year)
    polity_type = clean(row.get("polity_type"))
    founder = person_display(row.get("founder", ""), 24)
    capital = first_pipe_value(row.get("capital_historical") or row.get("capital_modern") or "", 24)
    successor = first_pipe_value(row.get("destroyed_by_or_successor", ""), 28)
    if boundary_kind == "start":
        if founder:
            sentence = f"{date}，{founder}建立{name}。"
        elif "诸侯" in polity_type and year <= -770:
            sentence = f"{date}，{name}受封建国。"
        elif is_major_polity(row):
            sentence = f"{date}，{name}建立。"
        else:
            sentence = f"{date}，{name}建国。"
        if capital:
            sentence = sentence[:-1] + f"，都城在{capital}。"
        return display_text(sentence)
    if is_transition_successor(successor):
        return display_text(f"{date}，{name}{successor}。")
    if successor and successor != name and name not in successor:
        return display_text(f"{date}，{name}亡于{successor}。")
    return display_text(f"{date}，{name}灭亡。")


def skips_generated_end_event(row: dict[str, str], year: int) -> bool:
    """Avoid turning a dataset endpoint into a false extinction event."""
    if year != YEAR_MAX:
        return False
    flags = clean(row.get("polity_name_risk_flags"))
    note = clean(row.get("confidence_note"))
    text = f"{flags}|{note}"
    return any(marker in text for marker in ("continues_after_1949", "year_endpoint", "数据集截断点", "截断点"))


def add_polity_boundary_event(
    events: list[dict[str, Any]],
    row: dict[str, str],
    boundary_kind: str,
    sort_order: int,
) -> None:
    polity_id = clean(row.get("polity_id"))
    if not polity_id:
        return
    year = parse_int(row.get("polity_start_year" if boundary_kind == "start" else "polity_end_year"))
    if year is None or year == 0 or year < YEAR_MIN or year > YEAR_MAX:
        return
    if boundary_kind == "end" and skips_generated_end_event(row, year):
        return
    event_type = "dynasty_start" if boundary_kind == "start" and is_major_polity(row) else "polity_start"
    if boundary_kind == "end":
        event_type = "dynasty_end" if is_major_polity(row) else "polity_end"
    stage = stage_for_polity(row, detail="period")
    major = is_major_polity(row)
    related_people = []
    if boundary_kind == "start":
        related_people = [first_pipe_value(row.get("founder", ""), 24)]
    else:
        related_people = [first_pipe_value(row.get("last_ruler", ""), 24)]
    source_titles = clean(row.get("polity_source_titles"))
    events.append(
        base_event_row(
            event_id=f"generated_{year_key(year)}_{polity_id}_{boundary_kind}",
            year=year,
            sort_order=sort_order,
            date_precision=boundary_precision(row),
            item_kind="representative_event",
            event_type=event_type,
            title=boundary_title(row, boundary_kind),
            description=boundary_description(row, boundary_kind, year),
            significance=f"标记{polity_display_name(row)}的{'建立' if boundary_kind == 'start' else '灭亡'}节点。",
            stage=stage,
            importance_level=5 if major else 3,
            display_priority=1 if major else 3,
            related_polity_ids=[polity_id],
            related_people=[person for person in related_people if person],
            location_name=first_pipe_value(row.get("capital_modern") or row.get("capital_historical") or "", 24),
            source_titles=source_titles,
            source_urls=clean(row.get("polity_source_urls")),
            source_type=source_type_for(source_titles),
            confidence_score=clean(row.get("confidence_score")),
            confidence_note=clean(row.get("confidence_note")) or "由政权标准表起止年生成，需结合来源复核",
        )
    )


def seed_covers_boundary(seed: dict[str, Any], polity_id: str, boundary_kind: str) -> bool:
    event_type = clean(seed.get("event_type"))
    boundary_types = {"dynasty_start", "polity_start"} if boundary_kind == "start" else {"dynasty_end", "polity_end"}
    return event_type in boundary_types and polity_id in split_pipe(seed.get("related_polity_ids", ""))


def add_year_summary(events: list[dict[str, Any]], year: int, groups: list[dict[str, Any]], order: int) -> None:
    names = [clean(group["first"].get("polity_name")) for group in groups[:8]]
    related_ids = [clean(group["first"].get("polity_id")) for group in groups[:8]]
    macro_periods = join_unique([clean(group["first"].get("macro_period")) for group in groups], 4)
    source_titles = join_unique([clean(group["first"].get("polity_source_titles")) for group in groups[:5]])
    source_urls = join_unique([clean(group["first"].get("polity_source_urls")) for group in groups[:5]])
    events.append(
        base_event_row(
            event_id=f"context_{year_key(year)}_polity_landscape",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="context",
            event_type="period_context",
            title=f"年度政权格局：{len(groups)}个政权并存",
            description=f"{year_label(year)}，v03 年度表记录 {len(groups)} 个可解析政权；代表性政权包括{ '、'.join(names[:6]) }。",
            significance=f"为播放视图提供本年政权并存背景；断代字段涉及{macro_periods or '未标注'}。",
            stage="初中" if len(groups) <= 5 else "高中",
            importance_level=2,
            display_priority=5,
            related_polity_ids=related_ids,
            source_titles=source_titles,
            source_urls=source_urls,
            source_type="derived_v03",
            confidence_score="",
            confidence_note="由 v03 年度展开表按 year 聚合生成；用于年度背景，不等同于单一突发事件",
        )
    )


def add_period_context(events: list[dict[str, Any]], year: int, groups: list[dict[str, Any]], order: int) -> None:
    macro_periods = join_unique([clean(group["first"].get("macro_period")) for group in groups], 5)
    dynasties = join_unique([clean(group["first"].get("dynasty_name")) for group in groups], 5)
    related_ids = [clean(group["first"].get("polity_id")) for group in groups[:6]]
    source_titles = join_unique([clean(group["first"].get("polity_source_titles")) for group in groups[:4]])
    source_urls = join_unique([clean(group["first"].get("polity_source_urls")) for group in groups[:4]])
    events.append(
        base_event_row(
            event_id=f"context_{year_key(year)}_period",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="context",
            event_type="period_context",
            title=f"断代脉络：{macro_periods or dynasties or '年度历史阶段'}",
            description=f"本年在 v03 断代字段中归入{macro_periods or '未标注大阶段'}；朝代/政权分组包括{dynasties or '未标注'}。",
            significance="帮助前端播放时把年度事实放回朝代与分裂并立背景中阅读。",
            stage="初中",
            importance_level=2,
            display_priority=5,
            related_polity_ids=related_ids,
            source_titles=source_titles,
            source_urls=source_urls,
            source_type="derived_v03",
            confidence_note="由 v03 macro_period 与 dynasty_name 字段生成",
        )
    )


def add_polity_status(events: list[dict[str, Any]], year: int, group: dict[str, Any], order: int) -> None:
    row = group["first"]
    polity_id = clean(row.get("polity_id"))
    name = clean(row.get("polity_name"))
    start = parse_int(row.get("polity_start_year"))
    end = parse_int(row.get("polity_end_year"))
    event_type = "polity_status"
    item_kind = "annual_fact"
    title = f"{name}持续存在"
    significance = f"记录{name}在{year_label(year)}的政权连续性。"
    importance = 3 if is_major_polity(row) else 2
    priority = 2 if is_major_polity(row) else 4
    if start == year:
        event_type = "dynasty_start" if is_major_polity(row) else "polity_start"
        item_kind = "representative_event" if is_major_polity(row) else "annual_fact"
        title = f"{name}起始年"
        significance = f"{name}在 v03 标准表中的起始年份为{year_label(year)}。"
        importance = 4 if is_major_polity(row) else 3
        priority = 2 if is_major_polity(row) else 3
    elif end == year:
        event_type = "dynasty_end" if is_major_polity(row) else "polity_end"
        item_kind = "representative_event" if is_major_polity(row) else "annual_fact"
        title = f"{name}终结年"
        successor = clean(row.get("destroyed_by_or_successor"))
        significance = f"{name}在 v03 标准表中的终止年份为{year_label(year)}" + (f"，后续/灭亡关系为{successor}。" if successor else "。")
        importance = 4 if is_major_polity(row) else 3
        priority = 2 if is_major_polity(row) else 3
    description = (
        f"{year_label(year)}，{name}作为{clean(row.get('polity_type')) or '政权'}"
        f"处于{clean(row.get('macro_period')) or clean(row.get('dynasty_name')) or '本年历史格局'}中；"
        f"v03 记录存在期为{clean(row.get('polity_start_label')) or start}至{clean(row.get('polity_end_label')) or end}。"
    )
    events.append(
        base_event_row(
            event_id=f"annual_{year_key(year)}_{polity_id}_status",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind=item_kind,
            event_type=event_type,
            title=title,
            description=description,
            significance=significance,
            stage=stage_for_polity(row, detail="status"),
            importance_level=importance,
            display_priority=priority,
            related_polity_ids=[polity_id],
            source_titles=clean(row.get("polity_source_titles")),
            source_urls=clean(row.get("polity_source_urls")),
            source_type=source_type_for(clean(row.get("polity_source_titles"))),
            confidence_score=clean(row.get("confidence_score")),
            confidence_note=clean(row.get("confidence_note")) or "由 v03 政权标准表与年度展开表生成",
        )
    )


def add_ruler_fact(events: list[dict[str, Any]], year: int, group: dict[str, Any], order: int) -> bool:
    row = group["first"]
    ruler_rows = group.get("rulers") or []
    if not ruler_rows:
        return False
    ruler = ruler_rows[0]
    polity_id = clean(row.get("polity_id"))
    polity_name = clean(row.get("polity_name"))
    ruler_name = (
        clean(ruler.get("ruler_name"))
        or clean(ruler.get("ruler_temple_name"))
        or clean(ruler.get("ruler_personal_name"))
        or clean(ruler.get("ruler_title"))
    )
    if not ruler_name:
        return False
    reign = ""
    if clean(ruler.get("ruler_reign_start_label")) or clean(ruler.get("ruler_reign_end_label")):
        reign = f"；v03 记录其统治期为{clean(ruler.get('ruler_reign_start_label'))}至{clean(ruler.get('ruler_reign_end_label'))}"
    era = f"；年号/纪年：{clean(ruler.get('era_names'))}" if clean(ruler.get("era_names")) else ""
    events.append(
        base_event_row(
            event_id=f"annual_{year_key(year)}_{polity_id}_{clean(ruler.get('ruler_id')) or deterministic_suffix(polity_id, ruler_name)}_ruler",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="annual_fact",
            event_type="ruler_reign",
            title=f"{polity_name}君主：{ruler_name}",
            description=f"{year_label(year)}，{polity_name}匹配到在位君主{ruler_name}{reign}{era}。",
            significance="用于把年度播放中的政权状态连接到君主纪年与教材叙事。",
            stage=stage_for_polity(row, detail="ruler"),
            importance_level=3 if is_major_polity(row) else 2,
            display_priority=3 if is_major_polity(row) else 4,
            related_polity_ids=[polity_id],
            related_people=[ruler_name],
            source_titles=clean(ruler.get("ruler_source_title")) or clean(row.get("polity_source_titles")),
            source_urls=clean(ruler.get("ruler_source_url")) or clean(row.get("polity_source_urls")),
            source_type=source_type_for(clean(ruler.get("ruler_source_title")) or clean(row.get("polity_source_titles"))),
            confidence_score=clean(ruler.get("ruler_confidence_score")) or clean(row.get("confidence_score")),
            confidence_note=clean(ruler.get("ruler_confidence_note")) or "由 v03 君主年表与年度展开表生成",
        )
    )
    return True


def add_capital_fact(
    events: list[dict[str, Any]],
    year: int,
    group: dict[str, Any],
    capitals_by_polity: dict[str, list[dict[str, str]]],
    order: int,
) -> bool:
    row = group["first"]
    polity_id = clean(row.get("polity_id"))
    capital = active_capital(capitals_by_polity, polity_id, year)
    if not capital:
        return False
    name = clean(capital.get("capital_name_historical")) or clean(capital.get("capital_name_modern"))
    modern = clean(capital.get("capital_name_modern"))
    precision = clean(capital.get("location_precision")) or "unknown"
    events.append(
        base_event_row(
            event_id=f"annual_{year_key(year)}_{polity_id}_{clean(capital.get('capital_event_id'))}_capital",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="annual_fact",
            event_type="capital_status",
            title=f"{clean(row.get('polity_name'))}都城：{name}",
            description=f"{year_label(year)}，{clean(row.get('polity_name'))}当前有效主都城记录为{name}" + (f"（今{modern}）" if modern and modern != name else "") + f"，定位精度为{precision}。",
            significance="用于在地图播放中解释都城标记与政权中心位置。",
            stage=stage_for_polity(row, detail="capital"),
            importance_level=3,
            display_priority=3 if is_major_polity(row) else 4,
            related_polity_ids=[polity_id],
            location_name=modern or name,
            longitude=clean(capital.get("longitude")),
            latitude=clean(capital.get("latitude")),
            source_titles=clean(capital.get("source_titles")),
            source_urls=clean(capital.get("source_urls")),
            source_type=source_type_for(clean(capital.get("source_titles"))),
            confidence_score=clean(capital.get("confidence_score")),
            confidence_note=clean(capital.get("confidence_note")) or "由 v03 都城事件表按年份匹配生成",
        )
    )
    return True


def add_geography_fact(events: list[dict[str, Any]], year: int, group: dict[str, Any], order: int) -> bool:
    row = group["first"]
    geography = clean(row.get("modern_admin_units_raw")) or clean(row.get("historical_geography_raw"))
    if not geography:
        return False
    polity_id = clean(row.get("polity_id"))
    events.append(
        base_event_row(
            event_id=f"annual_{year_key(year)}_{polity_id}_geography",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="annual_fact",
            event_type="territory_context",
            title=f"{clean(row.get('polity_name'))}地理范围记录",
            description=f"{year_label(year)}，v03 对{clean(row.get('polity_name'))}的现代行政区近似/历史地理文本记录为：{truncate(geography, 120)}",
            significance="用于说明地图疆域为现代行政区近似拼合，不是历史精确边界。",
            stage=stage_for_polity(row, detail="territory"),
            importance_level=2,
            display_priority=4,
            related_polity_ids=[polity_id],
            source_titles=clean(row.get("polity_source_titles")),
            source_urls=clean(row.get("polity_source_urls")),
            source_type=source_type_for(clean(row.get("polity_source_titles"))),
            confidence_score=clean(row.get("confidence_score")),
            confidence_note=clean(row.get("confidence_note")) or "由 v03 地理字段生成；现代行政区近似非历史精确边界",
        )
    )
    return True


def add_ruling_group_fact(events: list[dict[str, Any]], year: int, group: dict[str, Any], order: int) -> bool:
    row = group["first"]
    clan = clean(row.get("ruling_family_or_clan"))
    ethnicity = clean(row.get("ethnicity_or_group"))
    if not clan and not ethnicity:
        return False
    polity_id = clean(row.get("polity_id"))
    fragments = []
    if clan:
        fragments.append(f"统治家族/氏族为{clan}")
    if ethnicity:
        fragments.append(f"族属或群体标记为{ethnicity}")
    events.append(
        base_event_row(
            event_id=f"annual_{year_key(year)}_{polity_id}_ruling_group",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="annual_fact",
            event_type="ruling_group",
            title=f"{clean(row.get('polity_name'))}统治集团",
            description=f"{year_label(year)}，{clean(row.get('polity_name'))}{'，'.join(fragments)}。",
            significance="用于区分中原王朝、诸侯国和边疆/族群政权的统治背景。",
            stage=stage_for_polity(row, detail="ruler"),
            importance_level=2,
            display_priority=5,
            related_polity_ids=[polity_id],
            source_titles=clean(row.get("polity_source_titles")),
            source_urls=clean(row.get("polity_source_urls")),
            source_type=source_type_for(clean(row.get("polity_source_titles"))),
            confidence_score=clean(row.get("confidence_score")),
            confidence_note=clean(row.get("confidence_note")) or "由 v03 政权族属/氏族字段生成",
        )
    )
    return True


def add_source_context(events: list[dict[str, Any]], year: int, group: dict[str, Any], order: int) -> None:
    row = group["first"]
    source_raw = clean(row.get("polity_source_raw")) or clean(row.get("polity_date_raw"))
    source_raw = truncate(source_raw, 120) or "本年事实来自 v03 政权标准表与年度展开表。"
    events.append(
        base_event_row(
            event_id=f"context_{year_key(year)}_{clean(row.get('polity_id'))}_source",
            year=year,
            sort_order=order,
            date_precision="year",
            item_kind="context",
            event_type="source_context",
            title=f"{clean(row.get('polity_name'))}资料口径",
            description=source_raw,
            significance="保留本年自动生成事实的来源口径，便于后续人工复核。",
            stage="大学",
            importance_level=1,
            display_priority=5,
            related_polity_ids=[clean(row.get("polity_id"))],
            source_titles=clean(row.get("polity_source_titles")),
            source_urls=clean(row.get("polity_source_urls")),
            source_type=source_type_for(clean(row.get("polity_source_titles"))),
            confidence_score=clean(row.get("confidence_score")),
            confidence_note="由 v03 原始来源字段生成，作为复核上下文",
        )
    )


def build_events() -> tuple[list[dict[str, Any]], list[dict[str, Any]]]:
    raw_events = read_csv(EVENTS_CSV)
    seeds = normalize_seed_events(raw_events)
    events_by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    for seed in seeds:
        events_by_year[int(seed["year"])].append(seed)
    add_supplemental_events(events_by_year)

    boundary_candidates: dict[int, list[tuple[str, dict[str, str]]]] = defaultdict(list)
    for row in read_csv(MASTER_CSV):
        polity_id = clean(row.get("polity_id"))
        if not polity_id:
            continue
        for boundary_kind, year_field in (("start", "polity_start_year"), ("end", "polity_end_year")):
            year = parse_int(row.get(year_field))
            if year is None or year == 0 or year < YEAR_MIN or year > YEAR_MAX:
                continue
            if any(seed_covers_boundary(seed, polity_id, boundary_kind) for seed in events_by_year.get(year, [])):
                continue
            boundary_candidates[year].append((boundary_kind, row))

    for year, candidates in boundary_candidates.items():
        year_events = events_by_year[year]
        next_order = max([parse_int(event.get("sort_order"), 0) or 0 for event in year_events] or [0]) + 10
        for boundary_kind, row in sorted(
            candidates,
            key=lambda candidate: (
                0 if candidate[0] == "end" else 1,
                polity_rank(candidate[1]),
                clean(candidate[1].get("polity_id")),
            ),
        ):
            add_polity_boundary_event(year_events, row, boundary_kind, next_order)
            next_order += 10

    all_events: list[dict[str, Any]] = []
    for year_events in events_by_year.values():
        all_events.extend(
            sorted(
                year_events,
                key=lambda event: (
                    parse_int(event.get("sort_order"), 9999) or 9999,
                    clean(event.get("event_id")),
                ),
            )
        )

    sorted_events = sorted(all_events, key=lambda event: (int(event["year"]), parse_int(event.get("sort_order"), 9999) or 9999, clean(event.get("event_id"))))
    verified_events, review_rows = enriched_verified_events(sorted_events)
    return add_range_anchor_coverage(verified_events), review_rows


def validate_events(events: list[dict[str, Any]]) -> None:
    master_ids = {row["polity_id"] for row in read_csv(MASTER_CSV)}
    ids: set[str] = set()
    by_year: dict[int, list[dict[str, Any]]] = defaultdict(list)
    errors: list[str] = []
    for row in events:
        event_id = clean(row.get("event_id"))
        if event_id in ids:
            errors.append(f"duplicate event_id {event_id}")
        ids.add(event_id)
        year = parse_int(row.get("year"))
        if year is None or year == 0 or year < YEAR_MIN or year > YEAR_MAX:
            errors.append(f"{event_id}: invalid year {row.get('year')}")
            continue
        by_year[year].append(row)
        if clean(row.get("item_kind")) not in ITEM_KINDS:
            errors.append(f"{event_id}: invalid item_kind {row.get('item_kind')}")
        if clean(row.get("event_type")) in DISALLOWED_EVENT_TYPES:
            errors.append(f"{event_id}: display event uses removed event_type {row.get('event_type')}")
        if clean(row.get("date_precision")) not in DATE_PRECISIONS:
            errors.append(f"{event_id}: invalid date_precision {row.get('date_precision')}")
        coverage_role = clean(row.get("coverage_role"))
        if coverage_role not in COVERAGE_ROLES:
            errors.append(f"{event_id}: invalid coverage_role {row.get('coverage_role')}")
        if not clean(row.get("coverage_group_id")):
            errors.append(f"{event_id}: missing coverage_group_id")
        coverage_start = parse_int(row.get("coverage_start_year"))
        coverage_end = parse_int(row.get("coverage_end_year"))
        if coverage_start is None or coverage_end is None or coverage_start == 0 or coverage_end == 0:
            errors.append(f"{event_id}: invalid coverage range {row.get('coverage_start_year')}..{row.get('coverage_end_year')}")
        elif coverage_start > coverage_end or not (coverage_start <= year <= coverage_end):
            errors.append(f"{event_id}: coverage range does not include year")
        if coverage_role == "range_anchor" and clean(row.get("date_precision")) != "range":
            errors.append(f"{event_id}: range_anchor must use date_precision=range")
        if coverage_role != "range_anchor" and clean(row.get("date_precision")) == "range":
            errors.append(f"{event_id}: non-range coverage cannot use date_precision=range")
        if clean(row.get("primary_education_stage")) not in EDUCATION_STAGES:
            errors.append(f"{event_id}: invalid primary_education_stage {row.get('primary_education_stage')}")
        if clean(row.get("fact_review_status")) not in REVIEW_STATUSES:
            errors.append(f"{event_id}: invalid fact_review_status {row.get('fact_review_status')}")
        elif clean(row.get("fact_review_status")) != "verified":
            errors.append(f"{event_id}: formal event is not verified")
        if not clean(row.get("longitude")) or not clean(row.get("latitude")):
            errors.append(f"{event_id}: missing longitude/latitude")
        if not clean(row.get("location_historical_name")) or not clean(row.get("location_modern_name")):
            errors.append(f"{event_id}: missing historical/modern location name")
        if clean(row.get("location_precision")) not in LOCATION_PRECISIONS:
            errors.append(f"{event_id}: invalid location_precision {row.get('location_precision')}")
        loc_confidence = parse_int(row.get("location_confidence_score"))
        if loc_confidence is None or not (1 <= loc_confidence <= 100):
            errors.append(f"{event_id}: invalid location_confidence_score {row.get('location_confidence_score')}")
        if len(split_pipe(row.get("location_source_titles", ""))) < 2 or len(split_pipe(row.get("location_source_urls", ""))) < 2:
            errors.append(f"{event_id}: location needs at least two source references")
        source_count = min(len(split_pipe(row.get("source_titles", ""))), len(split_pipe(row.get("source_urls", ""))))
        if coverage_role in {"range_anchor", "annual_chronicle"}:
            if source_count < 1:
                errors.append(f"{event_id}: annual/range entry needs a verified source reference")
        elif source_count < 2:
            errors.append(f"{event_id}: core/representative event fact needs at least two source references")
        importance = parse_int(row.get("importance_level"))
        if importance is None or not (1 <= importance <= 5):
            errors.append(f"{event_id}: invalid importance_level {row.get('importance_level')}")
        priority = parse_int(row.get("display_priority"))
        if priority is None or not (1 <= priority <= 5):
            errors.append(f"{event_id}: invalid display_priority {row.get('display_priority')}")
        for polity_id in split_pipe(row.get("related_polity_ids", "")):
            if polity_id not in master_ids:
                errors.append(f"{event_id}: orphan related_polity_id {polity_id}")
        display_text_fields = " ".join(
            clean(row.get(field))
            for field in ("title", "description", "significance", "confidence_note")
        )
        for fragment in DISALLOWED_TEXT_FRAGMENTS:
            if fragment in display_text_fields:
                errors.append(f"{event_id}: display text still contains {fragment}")

    missing_years = [year for year in all_playable_years() if not by_year.get(year)]
    if missing_years:
        errors.append(f"missing historical_events for {len(missing_years)} years, first={missing_years[:12]}")

    if errors:
        preview = "\n".join(errors[:40])
        suffix = f"\n...and {len(errors) - 40} more" if len(errors) > 40 else ""
        raise SystemExit(f"historical_events_v03.csv validation failed:\n{preview}{suffix}")


def main() -> None:
    events, review_rows = build_events()
    validate_events(events)
    write_csv(EVENTS_CSV, events)
    write_review_report(EVENT_REVIEW_REPORT, review_rows)
    write_coverage_report(EVENT_COVERAGE_REPORT, events)
    years = {int(row["year"]) for row in events}
    print(
        "Generated historical_events_v03.csv:",
        f"{len(events)} rows,",
        f"{len(years)} event years,",
        f"{len(review_rows)} candidates held for review,",
        "full playable-year coverage verified",
    )
    print("Generated historical_event_coverage_report_v03.csv:", EVENT_COVERAGE_REPORT)


if __name__ == "__main__":
    main()
