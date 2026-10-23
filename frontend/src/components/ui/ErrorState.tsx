import { Button } from "./Button";

export interface ErrorStateProps {
  message: string;
  code?: string;
  onRetry?: () => void;
  retryLabel?: string;
}

export function ErrorState({ message, code, onRetry, retryLabel = "Try again" }: ErrorStateProps) {
  return (
    <div
      className="bv-card mx-auto flex max-w-lg flex-col items-center gap-3 px-6 py-8 text-center"
      role="alert"
    >
      <span aria-hidden="true" className="text-3xl">
        🛠️
      </span>
      <h2 className="text-lg font-bold">Something went sideways</h2>
      <p className="text-sm text-[var(--color-muted)]">{message}</p>
      {code ? (
        <code className="rounded bg-[#f5f1ec] px-2 py-1 text-xs text-[var(--color-muted)]">
          {code}
        </code>
      ) : null}
      {onRetry ? (
        <Button variant="primary" onClick={onRetry}>
          {retryLabel}
        </Button>
      ) : null}
    </div>
  );
}