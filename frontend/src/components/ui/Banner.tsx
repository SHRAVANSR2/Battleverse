import type { ReactNode } from "react";

type Tone = "info" | "demo" | "warn" | "danger" | "ok";

const toneClasses: Record<Tone, string> = {
  info: "border-[#ddd6fe] bg-[#f5f3ff] text-[#4338ca]",
  demo: "border-[#f0dfb8] bg-[#fdf6e6] text-[#7a5c2e]",
  warn: "border-[#fde68a] bg-[#fffbeb] text-[#92400e]",
  danger: "border-[#fecaca] bg-[#fef2f2] text-[#991b1b]",
  ok: "border-[#bbf7d0] bg-[#ecfdf3] text-[#166534]",
};

export interface BannerProps {
  tone?: Tone;
  children: ReactNode;
  role?: "status" | "alert";
  action?: ReactNode;
  className?: string;
}

export function Banner({
  tone = "info",
  children,
  role = "status",
  action,
  className = "",
}: BannerProps) {
  return (
    <div
      role={role}
      className={`flex flex-wrap items-center justify-between gap-3 rounded-2xl border px-4 py-3 text-sm ${toneClasses[tone]} ${className}`}
    >
      <div className="min-w-0">{children}</div>
      {action}
    </div>
  );
}