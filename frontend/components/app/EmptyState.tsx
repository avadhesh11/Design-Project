import { ReactNode } from "react";

interface EmptyStateProps {
  icon?: string;
  title: string;
  desc: string;
  action?: ReactNode;
}

export function EmptyState({ icon, title, desc, action }: EmptyStateProps) {
  return (
    <div className="flex flex-col items-center justify-center py-16 px-6 gap-3 text-center">
      {icon && (
        <div className="text-3xl opacity-25 mb-1">{icon}</div>
      )}
      <p className="text-sm font-medium text-orbit-text">{title}</p>
      <p className="text-xs text-orbit-muted max-w-xs leading-relaxed">{desc}</p>
      {action && <div className="mt-3">{action}</div>}
    </div>
  );
}
