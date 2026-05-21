#!/usr/bin/env python3
"""Validate input/vIndian/territory_overrides_vIndian.csv.

Checks:
- polity_id 存在于 input/vIndian/indian_history_polities_master_vIndian.csv 中。
- admin_ids 列中的每个 token 落在以下集合之一：
  * IN-XX → input/vIndian/admin_boundaries/india_adm1_normalized.geojson 中的 admin_id。
  * IN-ADM2-XXX → input/vIndian/admin_boundaries/india_adm2_normalized.geojson 中的 admin_id。
  * 3-letter ISO → input/vIndian/admin_boundaries/neighbor_adm0.geojson 中的 iso_a3。
  * IND → 全印度 ADM1 的便捷编码。
- 自由文本 token（不以 IN- 开头且非 3-letter ISO）被记为 warning，不算错误（允许过渡期）。
- valid_from_year ≤ valid_to_year，confidence_score 在 [0, 100]。

退出码 0 = 全部通过；1 = 有错误。
"""
from __future__ import annotations

import csv
import json
import sys
from pathlib import Path
from typing import Any


ROOT = Path(__file__).resolve().parents[1]
OVERRIDES_PATH = ROOT / "input" / "vIndian" / "territory_overrides_vIndian.csv"
MASTER_PATH = ROOT / "input" / "vIndian" / "indian_history_polities_master_vIndian.csv"
ADM1_PATH = ROOT / "input" / "vIndian" / "admin_boundaries" / "india_adm1_normalized.geojson"
ADM2_PATH = ROOT / "input" / "vIndian" / "admin_boundaries" / "india_adm2_normalized.geojson"
NEIGHBOR_PATH = ROOT / "input" / "vIndian" / "admin_boundaries" / "neighbor_adm0.geojson"


def read_csv(path: Path) -> list[dict[str, str]]:
    if not path.exists():
        return []
    with path.open("r", encoding="utf-8-sig", newline="") as f:
        return [dict(row) for row in csv.DictReader(f)]


def read_json(path: Path) -> Any:
    if not path.exists():
        return None
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def pipe_list(value: str | None) -> list[str]:
    if not value:
        return []
    return [v.strip() for v in str(value).split("|") if v.strip()]


def main() -> int:
    if not OVERRIDES_PATH.exists():
        print(f"ERROR: {OVERRIDES_PATH} not found", file=sys.stderr)
        return 1

    polities = read_csv(MASTER_PATH)
    valid_polity_ids = {(p.get("polity_id") or "").strip() for p in polities}

    adm1_data = read_json(ADM1_PATH) or {"features": []}
    valid_adm1 = {f["properties"]["admin_id"] for f in adm1_data["features"]}
    adm2_data = read_json(ADM2_PATH) or {"features": []}
    valid_adm2 = {f["properties"]["admin_id"] for f in adm2_data["features"]}
    neighbor_data = read_json(NEIGHBOR_PATH) or {"features": []}
    valid_iso = {(f["properties"].get("iso_a3") or "").upper() for f in neighbor_data["features"]}

    overrides = read_csv(OVERRIDES_PATH)
    errors: list[str] = []
    warnings: list[str] = []
    stats = {
        "total_rows": len(overrides),
        "with_admin_ids": 0,
        "fully_resolved": 0,
        "free_text_only": 0,
        "unmapped_polities": 0,
    }

    for i, row in enumerate(overrides, start=2):  # +1 for header, +1 for 1-based
        polity_id = (row.get("polity_id") or "").strip()
        if not polity_id:
            errors.append(f"row {i}: empty polity_id")
            continue
        if polity_id not in valid_polity_ids:
            errors.append(f"row {i}: polity_id {polity_id} not in master csv")

        admin_ids_raw = (row.get("admin_ids") or "").strip()
        tokens = pipe_list(admin_ids_raw)
        if not tokens:
            stats["unmapped_polities"] += 1
            continue
        stats["with_admin_ids"] += 1

        unknown_tokens: list[str] = []
        resolved_tokens: list[str] = []
        free_text_tokens: list[str] = []
        for token in tokens:
            if token.startswith("IN-ADM2-"):
                if token in valid_adm2:
                    resolved_tokens.append(token)
                else:
                    unknown_tokens.append(token)
            elif token.startswith("IN-"):
                if token in valid_adm1:
                    resolved_tokens.append(token)
                else:
                    unknown_tokens.append(token)
            elif token == "IND":
                resolved_tokens.append(token)
            elif len(token) == 3 and token.isupper():
                if token in valid_iso:
                    resolved_tokens.append(token)
                else:
                    unknown_tokens.append(token)
            else:
                free_text_tokens.append(token)

        for u in unknown_tokens:
            errors.append(f"row {i} (polity_id={polity_id}): unknown admin_id token '{u}'")

        if resolved_tokens and not free_text_tokens and not unknown_tokens:
            stats["fully_resolved"] += 1
        if free_text_tokens and not resolved_tokens:
            stats["free_text_only"] += 1
            warnings.append(
                f"row {i} (polity_id={polity_id}): admin_ids contains only free text "
                f"({', '.join(free_text_tokens)}); territory will not render."
            )
        elif free_text_tokens:
            warnings.append(
                f"row {i} (polity_id={polity_id}): mixed coded + free text "
                f"({', '.join(free_text_tokens)} ignored); coded tokens still render."
            )

        # 年份合法性
        try:
            from_year = int(row.get("valid_from_year") or 0)
        except ValueError:
            errors.append(f"row {i}: valid_from_year not integer ({row.get('valid_from_year')!r})")
            from_year = 0
        try:
            to_year = int(row.get("valid_to_year") or 0)
        except ValueError:
            errors.append(f"row {i}: valid_to_year not integer ({row.get('valid_to_year')!r})")
            to_year = 0
        if from_year and to_year and from_year > to_year:
            errors.append(f"row {i}: valid_from_year ({from_year}) > valid_to_year ({to_year})")

        # 置信度
        conf_raw = (row.get("confidence_score") or "").strip()
        if conf_raw:
            try:
                conf = float(conf_raw)
                if conf < 0 or conf > 100:
                    errors.append(f"row {i}: confidence_score out of range [0,100]: {conf}")
            except ValueError:
                errors.append(f"row {i}: confidence_score not numeric: {conf_raw!r}")

    print(f"[validate_territory_overrides_vIndian]")
    print(f"  total rows                : {stats['total_rows']}")
    print(f"  rows with admin_ids       : {stats['with_admin_ids']}")
    print(f"  fully resolved (renderable): {stats['fully_resolved']}")
    print(f"  free text only            : {stats['free_text_only']}")
    print(f"  unmapped polities         : {stats['unmapped_polities']}")
    print(f"  unmapped/total ratio       : {stats['unmapped_polities']}/{stats['total_rows']}")
    if warnings:
        print(f"\n  {len(warnings)} warnings:")
        for w in warnings[:20]:
            print(f"    - {w}")
        if len(warnings) > 20:
            print(f"    ... ({len(warnings) - 20} more)")
    if errors:
        print(f"\n  {len(errors)} ERRORS:")
        for e in errors[:30]:
            print(f"    - {e}")
        if len(errors) > 30:
            print(f"    ... ({len(errors) - 30} more)")
        return 1
    print("\n  OK (no errors)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
