import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter } from "react-router-dom";
import { NovaProvider } from "@/context/NovaContext";
import MiniWidget from "@/components/MiniWidget";
import MainLayout from "@/components/MainLayout";
import { useAuth } from "@/hooks/useAuth";
import AuthModal from "@/components/Auth";
import { useEffect } from "react";
import { useNova } from '@/context/NovaContext';

const queryClient = new QueryClient();

function AppContent() {
  const { state } = useNova();
  const { user } = useAuth();

  // NEW: Log mount for debugging
  useEffect(() => {
    console.log('APP: AppContent mounted, isMini:', isMiniFromUrl || isMiniFromGlobal);
  }, []);

  // FIXED: Detect mini ONLY via URL/global (Electron prod) or ?mini (dev)
  const urlParams = new URLSearchParams(window.location.search);
  const isMiniFromUrl = urlParams.get('mini') === 'true';
  const isMiniFromGlobal = typeof window !== 'undefined' && (window as any).isMiniMode;
  const isMini = isMiniFromUrl || isMiniFromGlobal;

  if (isMini) {
    return <MiniWidget unreadCount={2} />;
  }

  return <MainLayout />;
}

const App = () => {
  const { user, loading } = useAuth();

  // FIXED: Send auth status for both authenticated and unauthenticated states
  useEffect(() => {
    if (window.api) {
      if (user) {
        console.log('APP: Sending auth-status: true');
        window.api.setAuthStatus(true);
      } else {
        console.log('APP: Sending auth-status: false');
        window.api.setAuthStatus(false);
      }
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
              {!user && <AuthModal isOpen={true} onClose={() => {}} />}
              <AppContent />
            </div>
          </BrowserRouter>
        </NovaProvider>
      </TooltipProvider>
    </QueryClientProvider>
  );
};

export default App;