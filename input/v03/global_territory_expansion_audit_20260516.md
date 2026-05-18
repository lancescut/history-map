# v03 Batch 19 Global Territory Expansion Audit

Date: 2026-05-16

## Executive Summary

This audit verified the Batch 19 global-territory expansion against the actual `v03` CSV changes and a source-backed historical geography review. The current diff changes 68 polities in `historical_geography_raw` / `modern_admin_units_raw`, not 64. The yearly table is correctly synchronized by `polity_id`: after repair, every yearly row for these fields matches the master row.

The audit found two severe data errors and several over-broad territorial claims. The severe errors were:

1. `polity_0092` "汉" (551-552) was incorrectly described as Cheng-Han in Sichuan/Chongqing. It is Hou Jing's short-lived Han regime at Jiankang during the Hou Jing rebellion.
2. `polity_0009` "中天八国王" (942-943) was incorrectly described as a Dali/Yunnan regime. It was Zhang Yuxian's Southern Han-era uprising centered on Xunzhou/Boluo/Longchuan and later southern Jiangxi.

Batch 19 also records several polities that are not present in `chinese_history_polities_master_v03.csv`: 匈奴, 突厥, 回鹘, 吐蕃, 南诏, 大理, 高句丽, 渤海. These remain data-backlog items rather than delivered v03 records.

## Source-Backed Findings

### 1. Qin southern extent is disputed for northern Vietnam

The Qin entry previously stated "南至交趾" as if Qin control of northern Vietnam were settled. The Metropolitan Museum states that Qin Shihuang's empire eventually reached as far south as Vietnam [1], but Yoshikai's J-STAGE article explicitly argues that northern Vietnam was outside the Qin conquest area and became politically controlled under Nanyue, not Qin [2]. The CSV was changed to mark Xiang Commandery / Red River coverage as disputed.

### 2. Han and Eastern Han western reach should be Tarim-centered, not "Central Asia in bulk"

The Protectorate of the Western Regions was an imperial administration over the Western Regions, especially the Tarim Basin in southern Xinjiang [3]. That supports adding Xinjiang and eastern oasis influence, but not "Kyrgyzstan/Tajikistan大部" as stable direct control. The Western Han, Xin, Eastern Han, and Western Jin descriptions were revised to distinguish direct commanderies, protectorates, and stage-specific influence.

### 3. Vietnam-related fields need period-specific wording

Cambridge's 2025 Annan Protectorate article notes that Jiaozhi/Jiaozhou covered northern Vietnam over centuries, and that Jiaozhi, Jiuzhen, and Rinan corresponded to Vietnamese territories; it also notes direct Chinese rule was especially associated with Han and Eastern Wu phases [4]. Southern dynasties that only say "含交州" were therefore changed from broad "越南北部及中部" to "越南北部及中北部/控制有时期差异" where appropriate.

### 4. Shu Han should not include Myanmar as direct territory

Nanzhong is defined as parts of present-day Yunnan, Guizhou, and southern Sichuan, and it was part of Shu Han during the Three Kingdoms period [5]. The `蜀汉` row was changed to remove "缅甸北部部分地区" from the direct modern-territory string.

### 5. Tang and Wu Zhou require protectorate/loose-control language

The Tang created major protectorates including Anxi, Yanran/Anbei, Chanyu, Andong, Annan, and Beiting [4]. These support a broad maximum-extent note, but the data should not map them to modern countries as if all were stable direct rule. Tang and Wu Zhou rows were rewritten to mark military garrisons, protectorates, and jimi/loose control.

### 6. Yuan Korea and northern frontiers were over-broad

Goryeo became a semi-autonomous vassal and compulsory ally of Yuan for about 80 years, while retaining its own government structures in important respects [6]. Yuan's Manchuria control via Liaoyang province extended into the northeastern Korean Peninsula and Manchuria, but this is different from making "朝鲜半岛大部" direct Yuan territory [7]. The Yuan row was revised to separate direct/branch-secretariat control from Goryeo vassal status and to remove the "北冰洋" territorial claim.

### 7. Ming Nurgan was nominal and tribute/guard based

The Nurgan Regional Military Commission was established in Manchuria/Outer Manchuria, with Ming expeditions and titles reaching the lower Amur and Sakhalin; the same source describes nominal allegiance and tribute relationships [8]. The Ming row now uses "名义羁縻" and "朝贡影响区" instead of implying ordinary province-like control.

### 8. Qing Inner Asia is valid, but border wording must be precise

Qing expansion included Inner/Outer Mongolia, Manchuria/Outer Manchuria, Tibet, Qinghai, and Xinjiang [9]. Britannica notes Qing annexation west to Lake Balkhash [10]. The Qing row was retained as global in scope but revised to identify eastern Kazakhstan / Balkhash, northern-eastern Kyrgyzstan, and eastern Pamir as boundary or influence zones instead of an undifferentiated "外西北/塔吉克斯坦部分地区" claim.

### 9. Liao, Jin, and Western Liao broad additions are mostly acceptable with caution

Britannica locates Liao in Manchuria and Inner Mongolia, with a northern steppe government [11]. The Jurchen Jin source supports a peak extent from Outer Manchuria to the Qinling-Huaihe line [12]. Britannica's Karakitai entry supports Semirechye/Chu Valley and suzerainty over Transoxiana/Khwarezm [13]. These entries were not heavily rewritten in this pass, though Western Liao still merits a later specialist pass to separate direct domain from suzerainty.

## Corrections Applied

Corrected rows in master and cascaded to yearly:

- `polity_0092` 汉: corrected from Cheng-Han/Sichuan to Hou Jing's Jiankang regime.
- `polity_0009` 中天八国王: corrected from Dali/Yunnan to Zhang Yuxian's Lingnan uprising.
- `polity_0110`, `polity_0134`, `polity_0071`, `polity_0006`, `polity_0127`, `polity_0132`, `polity_0158`, `polity_0059`, `polity_0085`, `polity_0013`, `polity_0072`, `polity_0054`, `polity_0096`: revised over-broad global extent wording.
- `polity_0018`, `polity_0043`: normalized Qiu Chi modern geography from historical place names to modern regional descriptions.
- `polity_0005`, `polity_0017`, `polity_0038`, `polity_0083`, `polity_0157`: narrowed Vietnam/交州 wording to show period variation.

## Remaining Data Gaps

The following claimed Batch 19 categories are not present as v03 master polities and therefore remain missing from the actual baseline: 匈奴, 突厥, 回鹘, 吐蕃, 南诏, 大理, 高句丽, 渤海.

The public territory-generation pipeline remains China-ADM1 only. `territory_overrides_v03.csv` maps major dynasties to modern Chinese provincial boundaries, while non-China tokens in `modern_admin_units_raw` do not produce global polygons. A true global-territory baseline will need either global ADM1 boundaries plus a multilingual matcher, or polity-specific historical GIS geometries.

99 rows still have blank `historical_geography_raw`, mostly Zhou-period small states. `modern_admin_units_raw` is nonblank for all 167 master rows, but many are inherited place strings rather than normalized modern administrative units.

## Verification

- Master changed-polity count versus `HEAD`: 68.
- Master row count after repair: 167.
- Yearly row count after repair: 36,359 data rows plus header.
- Master/yearly consistency for `historical_geography_raw` and `modern_admin_units_raw`: 0 mismatches.

## Bibliography

[1] The Metropolitan Museum of Art. "Qin Dynasty (221-206 B.C.)." https://www.metmuseum.org/essays/qin-dynasty-221-206-b-c

[2] Masato Yoshikai. "A Note on the Early History of Lingnan and Northern Vietnam." J-STAGE. https://www.jstage.jst.go.jp/article/sea1971/2002/31/2002_31_79/_article

[3] "Protectorate of the Western Regions." Wikipedia. https://en.wikipedia.org/wiki/Protectorate_of_the_Western_Regions

[4] James A. Anderson. "The Annan Protectorate in northern Vietnam during the Tang period (679-907)." Journal of the Royal Asiatic Society / Cambridge Core. https://www.cambridge.org/core/journals/journal-of-the-royal-asiatic-society/article/annan-protectorate-in-northern-vietnam-during-the-tang-period-679907/0330A3F32086B5B1AEFC262A54FBF023

[5] "Nanzhong." Wikipedia. https://en.wikipedia.org/wiki/Nanzhong

[6] "Goryeo under Mongol rule." Wikipedia. https://en.wikipedia.org/wiki/Goryeo_under_Mongol_rule

[7] "Liaoyang (Yuan province)." Wikipedia. https://en.wikipedia.org/wiki/Liaoyang_%28Yuan_province%29

[8] "Nurgan Regional Military Commission." Wikipedia. https://en.wikipedia.org/wiki/Nurgan_Regional_Military_Commission

[9] "Qing dynasty in Inner Asia." Wikipedia. https://en.wikipedia.org/wiki/Qing_dynasty_in_Inner_Asia

[10] Encyclopaedia Britannica. "The Qing empire." https://www.britannica.com/place/China/The-Qing-empire

[11] Encyclopaedia Britannica. "Liao dynasty." https://www.britannica.com/topic/Liao-dynasty

[12] "Jin dynasty (1115-1234)." Wikipedia. https://en.wikipedia.org/wiki/Jin_dynasty_%281115%E2%80%931234%29

[13] Encyclopaedia Britannica. "Karakitai dynasty." https://www.britannica.com/topic/Karakitai-dynasty

[14] "張遇賢." Wikipedia. https://zh.wikipedia.org/wiki/%E5%BC%B5%E9%81%87%E8%B3%A2

[15] "太始 (侯景)." Wikipedia. https://zh.wikipedia.org/wiki/%E5%A4%AA%E5%A7%8B_%28%E4%BE%AF%E6%99%AF%29
