import type { ButtonHTMLAttributes, ReactNode } from "react";

type Variant = "primary" | "secondary" | "ghost" | "danger";
type Size = "sm" | "md" | "lg";

const variantClasses: Record<Variant, string> = {
  primary:
    "bg-[var(--color-primary)] text-white border-transparent shadow-[0_2px_0_#5b41d6] hover:bg-[#6f4ffb] active:translate-y-px active:shadow-none",
  secondary:
    "bg-white text-[var(--color-ink)] border-[var(--color-line)] hover:border-[#d9d1c8] hover:bg-[#fdfaf6]",
  ghost: "bg-transparent text-[var(--color-ink)] border-transparent hover:bg-[#f5f1ec]",
  danger:
    "bg-[#fef2f2] text-[var(--color-danger)] border-[#fecaca] hover:bg-[#fee2e2]",
};

const sizeClasses: Record<Size, string> = {
  sm: "min-h-[38px] px-3 text-sm",
  md: "min-h-[44px] px-4 text-[0.95rem]",
  lg: "min-h-[52px] px-6 text-base",
};

export interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: Variant;
  size?: Size;
  children: ReactNode;
  /** Renders a small inline spinner and sets aria-busy. */
  busy?: boolean;
}

export function Button({
  variant = "secondary",
  size = "md",
  busy = false,
  className = "",
  children,
  disabled,
  ...rest
}: ButtonProps) {
  return (
    <button
      {...rest}
      disabled={disabled || busy}
      aria-busy={busy || undefined}
      className={`bv-transition inline-flex items-center justify-center gap-2 rounded-full border font-semibold disabled:cursor-not-allowed disabled:opacity-55 ${variantClasses[variant]} ${sizeClasses[size]} ${className}`}
    >
      {busy ? <Spinner /> : null}
      {children}
    </button>
  );
}

export function Spinner({ label }: { label?: string }) {
  return (
    <span
      className="inline-block size-4 animate-spin rounded-full border-2 border-current border-t-transparent"
      role="img"
      aria-label={label ?? "Loading"}
    />
  );
}