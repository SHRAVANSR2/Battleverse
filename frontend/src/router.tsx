import { createBrowserRouter } from "react-router-dom";
import { HomePage } from "./pages/HomePage";
import { BattleSetupPage } from "./pages/BattleSetupPage";
import { BattleArenaPage } from "./pages/BattleArenaPage";
import { ResultsPage } from "./pages/ResultsPage";
import { HistoryPage } from "./pages/HistoryPage";
import { LeaderboardPage } from "./pages/LeaderboardPage";
import { NotFoundPage } from "./pages/NotFoundPage";

export const router = createBrowserRouter([
  { path: "/", element: <HomePage /> },
  { path: "/battle/new", element: <BattleSetupPage /> },
  { path: "/battle/:battleId", element: <BattleArenaPage /> },
  { path: "/battle/:battleId/result", element: <ResultsPage /> },
  { path: "/history", element: <HistoryPage /> },
  { path: "/leaderboard", element: <LeaderboardPage /> },
  { path: "*", element: <NotFoundPage /> },
]);