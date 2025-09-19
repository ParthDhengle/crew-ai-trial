// frontend/src/components/Auth.tsx
import React, { useState, useEffect } from 'react';  // Added useEffect
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/hooks/useAuth';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';
import { auth } from "../firebase"; // <-- make sure path is correct
import { GoogleAuthProvider, signInWithPopup } from "firebase/auth";
import { updateProfile } from "firebase/auth";


export default function AuthModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const { login, signup, user } = useAuth();

  // FIXED: Auto-close + Send IPC on success
  useEffect(() => {
    if (user && isOpen) {
      onClose();
      // New: Notify Electron main process
      if (window.api) {
        window.api.setAuthStatus(true);
      }
    }
  }, [user, isOpen, onClose]);

  const handleSubmit = async () => {
    try {
      if (isSignup) {
        await signup(email, password, email);
        if (auth.currentUser) {
          await updateProfile(auth.currentUser, { displayName: email.split('@')[0] });
        }
  // Use email as displayName
      } else {
        await login(email, password);
      }
    } catch (error) {
      alert((error as Error).message);
    }
  };

  if (!isOpen) return null;
  const handleGoogleSignIn = async () => {
    try {
      const provider = new GoogleAuthProvider();
      await signInWithPopup(auth, provider);
    } catch (error) {
      alert((error as Error).message);
    }
  };
  return (
    <Dialog open={true} onOpenChange={() => {}}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>{isSignup ? 'Sign Up' : 'Sign In'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
          <Button onClick={handleGoogleSignIn} className="w-full mt-4">Sign in with Google</Button>
          <Input placeholder="Email" value={email} onChange={(e) => setEmail(e.target.value)} />
          <Input type="password" placeholder="Password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Button onClick={handleSubmit} className="w-full">{isSignup ? 'Sign Up' : 'Sign In'}</Button>
          <Button variant="link" onClick={() => setIsSignup(!isSignup)} className="w-full">
            {isSignup ? 'Switch to Sign In' : 'Switch to Sign Up'}
          </Button>
        </div>
      </DialogContent>
    </Dialog>
  );
};