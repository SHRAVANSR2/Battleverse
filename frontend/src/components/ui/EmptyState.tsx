import type { ReactNode } from "react";

export interface EmptyStateProps {
  title: string;
  children?: ReactNode;
  action?: ReactNode;
  icon?: ReactNode;
}

export function EmptyState({ title, children, action, icon }: EmptyStateProps) {
  return (
    <div className="bv-card flex flex-col items-center gap-3 px-6 py-10 text-center">
      {icon ? <div className="text-[var(--color-muted)]">{icon}</div> : null}
      <h2 className="text-lg font-bold">{title}</h2>
      {children ? (
        <p className="max-w-md text-sm text-[var(--color-muted)]">{children}</p>
      ) : null}
      {action}
    </div>
  );
}