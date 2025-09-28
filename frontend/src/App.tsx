import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NovaProvider } from "@/context/NovaContext";
import { AuthProvider, useAuth } from "@/context/AuthContext";
import LoginForm from "@/components/LoginForm";
import MiniWidget from "@/components/MiniWidget"; // Assume this exists
import MainLayout from "@/components/MainLayout"; // NEW: Import MainLayout
import SchedulerKanban from "@/components/SchedulerKanban"; // Assume this exists
import DashboardCard from "@/components/DashboardCard"; // Assume this exists
import Settings from "@/components/Settings"; // Assume this exists
import { useNova } from "@/context/NovaContext";
import NotFound from "./pages/NotFound";
import { initializeApp } from 'firebase/app';
import ProfileSetupForm from "@/components/ProfileSetupForm";
import { useState, useEffect } from "react";

const queryClient = new QueryClient();
function AppContent() {
  const { isAuthenticated, isLoading, needsProfileSetup } = useAuth();
  const { state } = useNova();
  const [showProfileSetup, setShowProfileSetup] = useState(false);
  
  useEffect(() => {
    if (isAuthenticated && needsProfileSetup) {
      setShowProfileSetup(true);
    }
  }, [isAuthenticated, needsProfileSetup]);

  const handleProfileComplete = () => {
    setShowProfileSetup(false);
  }
  // Show loading while checking authentication
  if (isLoading) {
    return (
      <div className="flex items-center justify-center min-h-screen bg-background">
        <div className="text-center">
          <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-4" />
          <p className="text-muted-foreground">Loading Nova...</p>
        </div>
      </div>
    );
  }

  // Show login if not authenticated
  if (!isAuthenticated) {
    return <LoginForm />;
  }

  // Show profile setup if needed (NEW)
  if (showProfileSetup) {
    return <ProfileSetupForm onComplete={handleProfileComplete} />;
  }

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
      <AuthProvider>
        <NovaProvider>
          <BrowserRouter>
            <div className="min-h-screen w-full bg-background text-foreground overflow-hidden">
              <Routes>
                <Route path="/" element={<AppContent />} />
                <Route path="*" element={<NotFound />} />
              </Routes>
            </div>
          </BrowserRouter>
        </NovaProvider>
      </AuthProvider>
    </TooltipProvider>
  </QueryClientProvider>
);
export default App;