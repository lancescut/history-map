import type { ReactNode } from "react";

export function CollapsibleGroup({
  title,
  icon,
  collapsed,
  onToggle,
  children
}: {
  title: string;
  icon?: ReactNode;
  collapsed: boolean;
  onToggle: () => void;
  children: ReactNode;
}) {
  return (
    <section className={`layer-group ${collapsed ? "is-collapsed" : ""}`}>
      <button type="button" className="layer-group__head" onClick={onToggle}>
        <span className="layer-group__title">
          {icon ? <span className="layer-group__icon">{icon}</span> : null}
          {title}
        </span>
        <span className="layer-group__caret">{collapsed ? "▸" : "▾"}</span>
      </button>
      {!collapsed ? <div className="layer-group__body">{children}</div> : null}
    </section>
  );
}
