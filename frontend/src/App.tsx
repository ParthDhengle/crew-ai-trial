import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NovaProvider } from "@/context/NovaContext";
import MiniWidget from "@/components/MiniWidget"; // Assume this exists
import MainLayout from "@/components/MainLayout"; // NEW: Import MainLayout
import SchedulerKanban from "@/components/SchedulerKanban"; // Assume this exists
import DashboardCard from "@/components/DashboardCard"; // Assume this exists
import Settings from "@/components/Settings"; // Assume this exists
import { useNova } from "@/context/NovaContext";
import NotFound from "./pages/NotFound";
const queryClient = new QueryClient();
function AppContent() {
  const { state } = useNova();
  // FIXED: Detect mini ONLY via URL/global (Electron prod) or ?mini (dev). Ignore state.isMiniMode to avoid override after IPC switch.
  const urlParams = new URLSearchParams(window.location.search);
  const isMiniFromUrl = urlParams.get('mini') === 'true';
  const isMiniFromGlobal = typeof window !== 'undefined' && (window as any).isMiniMode;
  const isMini = isMiniFromUrl || isMiniFromGlobal;
  if (isMini) {
    return <MiniWidget unreadCount={2} />;
  }
  // FIXED: Removed redundant state.isMiniMode check—lets full UI render in mainWindow.
  return <MainLayout />;
}
const App = () => (
  <QueryClientProvider client={queryClient}>
    <TooltipProvider>
      <Toaster />
      <Sonner />
      <NovaProvider>
        <BrowserRouter>
          <div className="min-h-screen bg-background text-foreground">
            <Routes>
              <Route path="/" element={<AppContent />} />
              <Route path="*" element={<NotFound />} />
            </Routes>
          </div>
        </BrowserRouter>
      </NovaProvider>
    </TooltipProvider>
  </QueryClientProvider>
);
export default App;