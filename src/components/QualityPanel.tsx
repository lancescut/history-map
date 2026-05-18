import { issueTypeLabel } from "../event-meta";
import type { IssuesData, PolityIssue, ValidationData } from "../types";

export function QualityPanel({
  validation,
  issues,
  partialBoundaryPolities,
  onClose,
  onSelectPolity
}: {
  validation: ValidationData;
  issues: IssuesData | null;
  partialBoundaryPolities: PolityIssue[];
  onClose: () => void;
  onSelectPolity: (polityId: string) => void;
}) {
  const grouped = new Map<string, PolityIssue[]>();
  issues?.issues.forEach((issue) => {
    const list = grouped.get(issue.issue_type) ?? [];
    list.push(issue);
    grouped.set(issue.issue_type, list);
  });
  return (
    <div className="quality-panel">
      <div className="quality-panel__header">
        <div>
          <strong>数据质量</strong>
          <span>v03 · {validation.checks.length} 项校验 · {issues?.issues.length ?? 0} 条争议/口径说明</span>
        </div>
        <button type="button" onClick={onClose} aria-label="关闭数据质量面板">
          ×
        </button>
      </div>
      <ul className="quality-panel__checks">
        {validation.checks.map((check) => (
          <li
            key={check.check_name}
            className={`quality-check quality-check--${check.status.toLowerCase()}`}
          >
            <span className="quality-check__status">{check.status}</span>
            <span className="quality-check__name">{check.check_name}</span>
            <small>
              {check.checked_count} 行 · {check.issue_count} 异常
              {check.details ? ` · ${check.details}` : ""}
            </small>
          </li>
        ))}
      </ul>
      {partialBoundaryPolities.length ? (
        <div className="quality-panel__section">
          <strong>起止年部分缺失（partial_boundary）</strong>
          <div className="quality-panel__polity-list">
            {partialBoundaryPolities.map((issue) => (
              <button key={issue.issue_id} type="button" onClick={() => onSelectPolity(issue.polity_id)}>
                {issue.polity_display_name || issue.polity_name}
                <small>{issue.note}</small>
              </button>
            ))}
          </div>
        </div>
      ) : null}
      {Array.from(grouped.entries()).map(([type, list]) => (
        <details key={type} className="quality-panel__group">
          <summary>
            {issueTypeLabel(type)} · {list.length} 项
          </summary>
          <div className="quality-panel__polity-list">
            {list.map((issue) => (
              <button key={issue.issue_id} type="button" onClick={() => onSelectPolity(issue.polity_id)}>
                {issue.polity_display_name || issue.polity_name}
                <small>{issue.note}</small>
              </button>
            ))}
          </div>
        </details>
      ))}
    </div>
  );
}
