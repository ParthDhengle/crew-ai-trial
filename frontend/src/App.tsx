import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NovaProvider } from "@/context/NovaContext";
import MiniWidget from "@/components/MiniWidget";
import MainLayout from "@/components/MainLayout";
import SchedulerKanban from "@/components/SchedulerKanban";
import DashboardCard from "@/components/DashboardCard";
import Settings from "@/components/Settings";
import { useAuth } from "@/hooks/useAuth";
import AuthModal from "@/components/Auth";
import NotFound from "./pages/NotFound";
import { useEffect } from "react";
import { useNova } from '@/context/NovaContext';
const queryClient = new QueryClient();

function AppContent() {
  const { state } = useNova();  // FIXED: Import useNova here
  const { user } = useAuth();

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

const App = () => {
  const { user, loading } = useAuth();

  // New: Send auth success to Electron after login
  useEffect(() => {
    if (user && window.api) {
      window.api.setAuthStatus(true);
    }
  }, [user]);

  if (loading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        Loading...
      </div>
    );
  }

  return (
    <QueryClientProvider client={queryClient}>
      <TooltipProvider>
        <Toaster />
        <Sonner />
        <NovaProvider>
          <BrowserRouter>
            <div className="min-h-screen bg-background text-foreground">
              {/* New: Auth Overlay - Blocks everything if not logged in */}
              {!user && <AuthModal isOpen={true} onClose={() => {}} />}
              
              {/* Normal Routes */}
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
};

export default App;