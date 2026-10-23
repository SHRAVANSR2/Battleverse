import type { ReactNode } from "react";

type Tone = "neutral" | "ok" | "warn" | "danger" | "demo" | "accent";

const toneClasses: Record<Tone, string> = {
  neutral: "bg-[#f5f1ec] text-[var(--color-muted)] border-[var(--color-line)]",
  ok: "bg-[#ecfdf3] text-[var(--color-ok)] border-[#bbf7d0]",
  warn: "bg-[#fffbeb] text-[var(--color-warn)] border-[#fde68a]",
  danger: "bg-[#fef2f2] text-[var(--color-danger)] border-[#fecaca]",
  demo: "bg-[#fdf6e6] text-[var(--color-demo)] border-[#f0dfb8]",
  accent: "bg-[#f4f1ff] text-[var(--color-primary-ink)] border-[#ded5ff]",
};

export interface ChipProps {
  children: ReactNode;
  tone?: Tone;
  className?: string;
  title?: string;
}

export function Chip({ children, tone = "neutral", className = "", title }: ChipProps) {
  return (
    <span
      title={title}
      className={`inline-flex items-center gap-1.5 rounded-full border px-2.5 py-0.5 text-xs font-semibold tracking-wide uppercase ${toneClasses[tone]} ${className}`}
    >
      {children}
    </span>
  );
}