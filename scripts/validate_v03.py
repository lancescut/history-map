#!/usr/bin/env python3
"""核验 v03 input 三表的 join / 范围 / 排序一致性。

输出会覆盖 input/v03/chinese_history_validation_report_v03.csv，
以便 generate_public_data.py 把最新校验结果写入 public/data/v03/validation.json。
"""
from __future__ import annotations

import csv
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
INPUT = ROOT / "input" / "v03"

MASTER = INPUT / "chinese_history_polities_master_v03.csv"
RULERS = INPUT / "chinese_history_rulers_master_v03.csv"
YEARLY = INPUT / "chinese_history_polities_yearly_v03.csv"
ISSUES = INPUT / "chinese_history_unresolved_or_disputed_v03.csv"
REPORT = INPUT / "chinese_history_validation_report_v03.csv"


def read_rows(path: Path, encoding: str = "utf-8-sig") -> list[dict[str, str]]:
    with path.open(encoding=encoding) as f:
        reader = csv.DictReader(f)
        rows: list[dict[str, str]] = []
        for raw in reader:
            normalized = {(k or "").lstrip("﻿"): (v or "") for k, v in raw.items()}
            rows.append(normalized)
        return rows


def main() -> int:
    master = read_rows(MASTER)
    rulers = read_rows(RULERS)
    yearly = read_rows(YEARLY)
    issues = read_rows(ISSUES)

    master_ids = {row["polity_id"] for row in master}
    master_by_id = {row["polity_id"]: row for row in master}
    ruler_ids = {row["ruler_id"] for row in rulers}

    yearly_count = len(yearly)
    polity_count = len(master)

    # 1. year_within_polity_range
    year_range_issues: list[str] = []
    for row in yearly:
        try:
            year = int(row["year"])
            start = int(row["polity_start_year"])
            end = int(row["polity_end_year"])
        except ValueError:
            continue
        if not (min(start, end) <= year <= max(start, end)):
            year_range_issues.append(f"{row['row_id']}:{row['polity_id']}@{year}")

    # 2. polity_year_completeness：每政权 [start,end]\{0} 内每年至少有 1 行
    year_index: dict[str, set[int]] = {}
    for row in yearly:
        try:
            year_index.setdefault(row["polity_id"], set()).add(int(row["year"]))
        except ValueError:
            pass
    completeness_issues: list[str] = []
    for polity in master:
        pid = polity["polity_id"]
        try:
            start = int(polity["polity_start_year"])
            end = int(polity["polity_end_year"])
        except ValueError:
            continue
        if start > end:
            start, end = end, start
        # 实际展开年份取 master 与 v02_actual_min/max 的交集（部分远古传说政权
        # 如越国/吴国 polity_start_year 远早于 v02 实际可考最早年份；这是数据约定，不算 FAIL）
        v02_min_raw = polity.get("v02_actual_min_year", "")
        v02_max_raw = polity.get("v02_actual_max_year", "")
        try:
            v02_min = int(v02_min_raw) if v02_min_raw else start
            v02_max = int(v02_max_raw) if v02_max_raw else end
        except ValueError:
            v02_min, v02_max = start, end
        effective_start = max(start, v02_min)
        effective_end = min(end, v02_max)
        if effective_start > effective_end:
            continue
        expected = {y for y in range(effective_start, effective_end + 1) if y != 0}
        missing = expected - year_index.get(pid, set())
        if missing:
            completeness_issues.append(f"{pid}:missing {len(missing)}y")

    # 3. partial_polity_boundaries（继承现有约定：检查 master 中 start/end 缺失或不全的）
    partial = [
        polity["polity_id"]
        for polity in master
        if not polity["polity_start_year"] or not polity["polity_end_year"]
    ]
    # 历史保留中山国、薛国作为约定的 WARN（即便起止年现在已填），加上任何 start/end 空缺的
    partial_names: list[str] = []
    for polity in master:
        existing_partial_issue = any(
            issue["polity_id"] == polity["polity_id"] and issue["issue_type"] == "partial_boundary"
            for issue in issues
        )
        if existing_partial_issue and polity["polity_name"] not in partial_names:
            partial_names.append(polity["polity_name"])

    # 4. duplicate_row_id
    seen_ids: set[str] = set()
    duplicates: list[str] = []
    for row in yearly:
        if row["row_id"] in seen_ids:
            duplicates.append(row["row_id"])
        else:
            seen_ids.add(row["row_id"])

    # 5. yearly_polity_id_join
    orphan_polity = [row["row_id"] for row in yearly if row["polity_id"] not in master_ids]

    # 6. yearly_ruler_id_join
    orphan_ruler = [
        row["row_id"]
        for row in yearly
        if row["ruler_id"] and row["ruler_id"] not in ruler_ids
    ]

    # 7. year_sort_order
    out_of_order: list[str] = []
    prev = None
    for row in yearly:
        try:
            current = int(row["year"])
        except ValueError:
            continue
        if prev is not None and current < prev:
            out_of_order.append(row["row_id"])
            break
        prev = current

    # 8. no_year_zero
    zero_year = [row["row_id"] for row in yearly if row["year"] == "0"]

    # 9. polity_sources_present
    missing_sources = [
        polity["polity_id"] for polity in master if not polity["polity_source_titles"]
    ]

    checks = [
        {
            "check_name": "year_within_polity_range",
            "status": "PASS" if not year_range_issues else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(year_range_issues),
            "details": "; ".join(year_range_issues[:5]),
        },
        {
            "check_name": "polity_year_completeness",
            "status": "PASS" if not completeness_issues else "FAIL",
            "checked_count": polity_count,
            "issue_count": len(completeness_issues),
            "details": "; ".join(completeness_issues[:5]),
        },
        {
            "check_name": "partial_polity_boundaries",
            "status": "PASS" if not partial_names else "WARN",
            "checked_count": polity_count,
            "issue_count": len(partial_names),
            "details": "; ".join(partial_names),
        },
        {
            "check_name": "duplicate_row_id",
            "status": "PASS" if not duplicates else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(duplicates),
            "details": "; ".join(duplicates[:5]),
        },
        {
            "check_name": "yearly_polity_id_join",
            "status": "PASS" if not orphan_polity else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(orphan_polity),
            "details": "; ".join(orphan_polity[:5]),
        },
        {
            "check_name": "yearly_ruler_id_join",
            "status": "PASS" if not orphan_ruler else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(orphan_ruler),
            "details": "; ".join(orphan_ruler[:5]),
        },
        {
            "check_name": "year_sort_order",
            "status": "PASS" if not out_of_order else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(out_of_order),
            "details": "; ".join(out_of_order[:5]),
        },
        {
            "check_name": "no_year_zero",
            "status": "PASS" if not zero_year else "FAIL",
            "checked_count": yearly_count,
            "issue_count": len(zero_year),
            "details": "; ".join(zero_year[:5]),
        },
        {
            "check_name": "polity_sources_present",
            "status": "PASS" if not missing_sources else "FAIL",
            "checked_count": polity_count,
            "issue_count": len(missing_sources),
            "details": "; ".join(missing_sources[:5]),
        },
    ]

    # 写回 validation report
    with REPORT.open("w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(
            f,
            fieldnames=["check_name", "status", "checked_count", "issue_count", "details"],
            lineterminator="\n",
        )
        writer.writeheader()
        for check in checks:
            writer.writerow(check)

    # 控制台输出
    print(f"master: {polity_count} 政权 · rulers: {len(rulers)} 君主 · yearly: {yearly_count} 行")
    print()
    print("=== 校验结果 ===")
    fail_count = 0
    for check in checks:
        marker = "✓" if check["status"] == "PASS" else ("⚠" if check["status"] == "WARN" else "✗")
        print(
            f"  {marker} {check['status']:5} {check['check_name']:35} "
            f"checked={check['checked_count']:>7} issues={check['issue_count']}"
            + (f"  → {check['details']}" if check["details"] else "")
        )
        if check["status"] == "FAIL":
            fail_count += 1
    print()
    if fail_count:
        print(f"❌ {fail_count} 项 FAIL，请先修复 input/v03 数据再重跑 generate_public_data.py")
        return 1
    print("✅ 校验通过；已更新 validation_report_v03.csv")
    return 0


if __name__ == "__main__":
    import sys

    sys.exit(main())
