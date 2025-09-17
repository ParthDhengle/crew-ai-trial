// frontend/src/components/Auth.tsx
import React, { useState } from 'react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { useAuth } from '@/hooks/useAuth';
import { Dialog, DialogContent, DialogHeader, DialogTitle } from '@/components/ui/dialog';

export default function AuthModal({ isOpen, onClose }: { isOpen: boolean; onClose: () => void }) {
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');
  const [isSignup, setIsSignup] = useState(false);
  const { login, signup } = useAuth();

  const handleSubmit = async () => {
    try {
      if (isSignup) {
        await signup(email, password);
      } else {
        await login(email, password);
      }
      onClose();
    } catch (error) {
      alert((error as Error).message);
    }
  };

  return (
    <Dialog open={isOpen} onOpenChange={onClose}>
      <DialogContent>
        <DialogHeader>
          <DialogTitle>{isSignup ? 'Sign Up' : 'Sign In'}</DialogTitle>
        </DialogHeader>
        <div className="space-y-4">
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