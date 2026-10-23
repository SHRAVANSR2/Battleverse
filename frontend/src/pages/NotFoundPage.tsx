import { Link } from "react-router-dom";
import { AppShell } from "../components/layout/AppShell";
import { EmptyState } from "../components/ui/EmptyState";
import { RobotAvatar } from "../components/character/RobotAvatar";
import { useDocumentTitle } from "../hooks/useDocumentTitle";

export function NotFoundPage() {
  useDocumentTitle("Not found");
  return (
    <AppShell narrow>
      <EmptyState
        title="This page wandered off"
        icon={<RobotAvatar accent="mint" size={90} />}
        action={
          <Link
            to="/"
            className="mt-1 inline-flex min-h-[44px] items-center rounded-full bg-[var(--color-primary)] px-5 font-semibold text-white no-underline"
          >
            Back home
          </Link>
        }
      >
        The robots checked twice. Nothing here.
      </EmptyState>
    </AppShell>
  );
}