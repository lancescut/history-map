import type { HistoricalEvent } from "./types";

// 事件类型与争议项的标签/字形映射，跨组件共享。
// 历史事件类型：关键事件、战争统一、王朝/政权起灭；issue 3 种类型见 issues.json。

export const EVENT_TYPE_LABELS: Record<string, string> = {
  unification: "统一",
  war: "战役",
  dynasty_start: "立朝",
  dynasty_end: "亡国",
  event: "事件",
  polity_start: "建国",
  polity_end: "灭亡",
  reform: "改革",
  institution: "制度",
  diplomacy: "外交",
  treaty: "条约",
  culture: "文化",
  infrastructure: "工程",
  trade: "贸易",
  capital_relocation: "迁都",
  occupation: "占领",
  retrocession: "收回",
  cession: "割让",
  civil_war_control: "战线",
  range_anchor: "进程",
  allusion: "典故"
};

export const EVENT_TYPE_GLYPHS: Record<string, string> = {
  unification: "★",
  war: "✦",
  dynasty_start: "▲",
  dynasty_end: "▽",
  event: "●",
  polity_start: "△",
  polity_end: "▿",
  reform: "◆",
  institution: "■",
  diplomacy: "◇",
  treaty: "□",
  culture: "●",
  infrastructure: "■",
  trade: "◇",
  capital_relocation: "▲",
  occupation: "✦",
  retrocession: "□",
  cession: "□",
  civil_war_control: "✦",
  range_anchor: "·",
  allusion: "典"
};

export function eventTypeLabel(eventType: string): string {
  return EVENT_TYPE_LABELS[eventType] ?? eventType;
}

export const COVERAGE_ROLE_LABELS: Record<string, string> = {
  exact_year_event: "精确",
  annual_chronicle: "编年",
  range_anchor: "进程",
  nearby_enrichment: "邻年",
  anecdote: "典故"
};

export function coverageRoleLabel(role: string): string {
  return COVERAGE_ROLE_LABELS[role] ?? role;
}

export function historicalEventPlaybackKey(event: HistoricalEvent): string {
  if (event.is_anecdote || event.item_kind === "anecdote") return `anecdote:${event.anecdote_id ?? event.event_id}`;
  if (event.coverage_group_id) return event.coverage_group_id;
  if (event.coverage_role === "range_anchor") {
    return [
      "range_anchor",
      event.coverage_start_year,
      event.coverage_end_year,
      event.title
    ].join(":");
  }
  return event.event_id;
}

export const ISSUE_TYPE_LABELS: Record<string, string> = {
  merged_v02_contexts: "异名/简繁合并",
  partial_boundary: "起止年部分缺失",
  chronology_variant: "纪年口径差异"
};

export function issueTypeLabel(issueType: string): string {
  return ISSUE_TYPE_LABELS[issueType] ?? issueType;
}
