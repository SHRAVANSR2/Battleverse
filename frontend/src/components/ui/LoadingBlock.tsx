import { Spinner } from "./Button";

export function LoadingBlock({ label = "Loading…" }: { label?: string }) {
  return (
    <div
      className="flex items-center justify-center gap-3 py-16 text-sm text-[var(--color-muted)]"
      role="status"
      aria-live="polite"
    >
      <Spinner label={label} />
      {label}
    </div>
  );
}