// src/App.tsx
import { useState } from "react";
import { Toaster } from "@/components/ui/toaster";
import { Toaster as Sonner } from "@/components/ui/sonner";
import { TooltipProvider } from "@/components/ui/tooltip";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { BrowserRouter, Routes, Route } from "react-router-dom";
import { NovaProvider, useNova } from "@/context/NovaContext";
import MiniWidget from "@/components/MiniWidget";
import MainLayout from "@/components/MainLayout";
import NotFound from "./pages/NotFound";
import { useAuth } from "./hooks/useAuth";
import AuthModal from "./components/Auth";

const queryClient = new QueryClient();

function AppContent() {
  const { state } = useNova();
  const { user, loading } = useAuth();
  const [showAuth, setShowAuth] = useState(!user && !loading);

  // Mini-mode detection (Electron mini window)
  const urlParams = new URLSearchParams(window.location.search);
  const isMiniFromUrl = urlParams.get("mini") === "true";
  const isMiniFromGlobal =
    typeof window !== "undefined" && (window as any).isMiniMode;
  const isMini = isMiniFromUrl || isMiniFromGlobal;

  if (loading) return <div>Loading...</div>;
  if (isMini) return <MiniWidget unreadCount={2} />;

  return (
    <>
      <MainLayout />
      <AuthModal isOpen={showAuth} onClose={() => setShowAuth(false)} />
    </>
  );
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
