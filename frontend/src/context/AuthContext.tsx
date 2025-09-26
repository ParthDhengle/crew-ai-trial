// frontend/src/context/AuthContext.tsx
import { getAuth, signInWithCustomToken, onAuthStateChanged, User as FirebaseUser } from "firebase/auth";
import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import { apiClient, authManager } from '@/api/client';

interface User {
  uid: string;
  email?: string;
  displayName?: string;
  role?: string;
  location?: string;
  productiveTime?: string;
  topMotivation?: string;
  aiTone?: string;
  profileComplete: boolean;
}

interface AuthState {
  user: User | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;
  needsProfileSetup: boolean;
}

interface AuthContextType extends AuthState {
  login: (email: string, password: string) => Promise<{ needsProfileSetup: boolean }>;
  signup: (email: string, password: string) => Promise<{ needsProfileSetup: boolean }>;
  logout: () => Promise<void>;
  completeProfile: (profileData: any) => Promise<void>;
  clearError: () => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

interface AuthProviderProps {
  children: ReactNode;
}

// Define profile response type
interface ProfileResponse {
  uid: string;
  email: string;
  Name?: string;
  display_name?: string;
  role?: string;
  location?: string;
  productive_time?: string;
  top_motivation?: string;
  ai_tone?: string;
  profile_complete: boolean;
  [key: string]: any;
}

export function AuthProvider({ children }: AuthProviderProps) {
  const [state, setState] = useState<AuthState>({
    user: null,
    isAuthenticated: false,
    isLoading: true,
    error: null,
    needsProfileSetup: false,
  });

  const auth = getAuth();

  // Listen to Firebase auth state changes (handles persistence)
  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser: FirebaseUser | null) => {
      if (firebaseUser) {
        const uid = firebaseUser.uid;
        try {
          const profile = await apiClient.getProfile() as ProfileResponse;
          const needsSetup = !profile.profile_complete;
          
          setState({
            user: { 
              uid, 
              email: profile.email,
              displayName: profile.display_name || profile.Name,
              role: profile.role,
              location: profile.location,
              productiveTime: profile.productive_time,
              topMotivation: profile.top_motivation,
              aiTone: profile.ai_tone,
              profileComplete: profile.profile_complete
            },
            isAuthenticated: true,
            isLoading: false,
            error: null,
            needsProfileSetup: needsSetup,
          });
          authManager.setAuth('', uid); // Optional: Store UID only if needed elsewhere
        } catch (error) {
          console.error('Failed to fetch profile:', error);
          setState(prev => ({ ...prev, error: 'Failed to load profile', isLoading: false }));
        }
      } else {
        authManager.clearAuth();
        setState({
          user: null,
          isAuthenticated: false,
          isLoading: false,
          error: null,
          needsProfileSetup: false,
        });
      }
    });

    return unsubscribe;
  }, []);

  const login = async (email: string, password: string): Promise<{ needsProfileSetup: boolean }> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await apiClient.login(email, password); // Gets custom_token and profile_complete
      await signInWithCustomToken(auth, response.custom_token); // Exchange; auth state will update via listener
      return { needsProfileSetup: !response.profile_complete };
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : 'Login failed';
      setState(prev => ({ ...prev, isLoading: false, error: errMsg }));
      throw error;
    }
  };

  const signup = async (email: string, password: string): Promise<{ needsProfileSetup: boolean }> => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      const response = await apiClient.signup(email, password);
      await signInWithCustomToken(auth, response.custom_token); // Same as login
      return { needsProfileSetup: !response.profile_complete };
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : 'Signup failed';
      setState(prev => ({ ...prev, isLoading: false, error: errMsg }));
      throw error;
    }
  };

  const completeProfile = async (profileData: any) => {
    setState(prev => ({ ...prev, isLoading: true, error: null }));
    try {
      await apiClient.completeProfile(profileData);
      // Refresh profile data
      const profile = await apiClient.getProfile() as ProfileResponse;
      setState(prev => ({
        ...prev,
        user: prev.user ? {
          ...prev.user,
          displayName: profile.display_name || profile.Name,
          role: profile.role,
          location: profile.location,
          productiveTime: profile.productive_time,
          topMotivation: profile.top_motivation,
          aiTone: profile.ai_tone,
          profileComplete: profile.profile_complete
        } : null,
        needsProfileSetup: false,
        isLoading: false,
      }));
    } catch (error) {
      const errMsg = error instanceof Error ? error.message : 'Profile completion failed';
      setState(prev => ({ ...prev, isLoading: false, error: errMsg }));
      throw error;
    }
  };

  const logout = async () => {
    try {
      await auth.signOut();
      apiClient.logout(); // Clear any backend sessions if needed
    } catch (error) {
      console.error('Logout failed:', error);
    }
  };

  const clearError = () => {
    setState(prev => ({ ...prev, error: null }));
  };

  return (
    <AuthContext.Provider value={{ ...state, login, signup, logout, completeProfile, clearError }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const context = useContext(AuthContext);
  if (!context) {
    throw new Error('useAuth must be used within an AuthProvider');
  }
  return context;
}