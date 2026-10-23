import type { ReactNode } from "react";
import { NavBar } from "./NavBar";

export interface AppShellProps {
  children: ReactNode;
  /** Constrain to a narrower column (forms, results). */
  narrow?: boolean;
}

export function AppShell({ children, narrow = false }: AppShellProps) {
  return (
    <div className="flex min-h-dvh flex-col">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-4 focus:z-50 focus:rounded-full focus:bg-white focus:px-4 focus:py-2 focus:shadow-[var(--shadow-lift)]"
      >
        Skip to content
      </a>
      <NavBar />
      <main
        id="main"
        className={`mx-auto w-full flex-1 px-4 py-6 sm:py-10 ${narrow ? "max-w-3xl" : "max-w-5xl"}`}
      >
        {children}
      </main>
      <footer className="mx-auto w-full max-w-5xl px-4 pb-8 pt-2 text-center text-xs text-[var(--color-muted)]">
        BattleVerse · local-first robot rap battles ·{" "}
        <span title="Verses come from Groq when a key is configured; otherwise a clearly labelled scripted writer runs.">
          Groq-powered when configured
        </span>
      </footer>
    </div>
  );
}