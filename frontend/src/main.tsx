import { createRoot } from "react-dom/client";
import App from "./App.tsx";
import "./index.css";
import { NovaProvider } from './context/NovaContext';
createRoot(document.getElementById("root")!).render(
<NovaProvider>
    <App />
  </NovaProvider>
);
