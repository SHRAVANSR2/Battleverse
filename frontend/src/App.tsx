import { RouterProvider } from "react-router-dom";
import { AudioProvider } from "./audio/AudioProvider";
import { router } from "./router";

export function App() {
  return (
    <AudioProvider>
      <RouterProvider router={router} />
    </AudioProvider>
  );
}