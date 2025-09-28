/**
 * Nova AI Assistant - Login Form Component
 * 
 * Handles user authentication with email/password
 */

import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Eye, EyeOff, Loader2, Mail, Lock, UserPlus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs';
import { useAuth } from '@/context/AuthContext';
import {
  Minimize2 ,
  X,
  Minus,
  Maximize2 // Added for close functionality
} from 'lucide-react';
interface LoginFormProps {
  onSuccess?: (needsProfileSetup?: boolean) => void;
  className?: string;
}
import { useWindowControls } from '@/hooks/useElectronApi';

export default function LoginForm({ onSuccess, className = '' }: LoginFormProps) {
  const { login, signup, isLoading, error, clearError } = useAuth();
  const [activeTab, setActiveTab] = useState('login');
  const [showPassword, setShowPassword] = useState(false);
  const [formData, setFormData] = useState({
    email: '',
    password: '',
    confirmPassword: '',
  });
  const { expand, close, minimize,contract } = useWindowControls();

  const handleInputChange = (field: string) => (e: React.ChangeEvent<HTMLInputElement>) => {
    setFormData(prev => ({ ...prev, [field]: e.target.value }));
    if (error) clearError();
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    
    if (activeTab === 'signup' && formData.password !== formData.confirmPassword) {
      return;
    }
    try {
      let result: { needsProfileSetup: boolean };
      
      if (activeTab === 'login') {
        result = await login(formData.email, formData.password);
      } else {
        result = await signup(formData.email, formData.password);
      }
      onSuccess?.(result.needsProfileSetup);
    } catch (error) {
      // Error is handled by the auth context
    }
  };

  const isFormValid = () => {
    if (activeTab === 'login') {
      return formData.email && formData.password;
    } else {
      return formData.email && formData.password && formData.confirmPassword && 
             formData.password === formData.confirmPassword;
    }
  };

  return (
    <div className={`flex items-center justify-center min-h-screen bg-background ${className}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-md"
      >

{/* Window Title Bar */}
<div 
        className={`flex items-center justify-between px-4 py-2 bg-background/95 backdrop-blur-sm border-b border-border/50 ${className}`}
        style={{ 
          ['WebkitAppRegion' as any]: 'drag',
          userSelect: 'none'
        }}
      >
        {/* Title */}
        <div className="flex items-center space-x-2">
          <span className="ml-3 text-sm font-medium text-foreground/80">
            "Nova Chat Assistant"
          </span>
        </div>

        {/* Window Controls */}
        <div className="flex items-center space-x-1" style={{ ['WebkitAppRegion' as any]: 'no-drag' }}>
          <Button
            size="sm"
            variant="ghost"
            onClick={minimize}
            className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
            title="Minimize"
          >
            <Minus size={12} />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={expand}
            className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
            title="Maximize"
          >
            <Maximize2 size={12} />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={close}
            className="w-6 h-6 p-0 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-none"
            title="Close"
          >
            <X size={12} />
          </Button>
        </div>
      </div>

        <Card className="glass-nova border-primary/20">
          <CardHeader className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold text-primary-foreground">
              N
            </div>
            <CardTitle className="text-2xl font-bold">Welcome to Nova</CardTitle>
            <CardDescription>
              Your AI assistant for productivity and creativity
            </CardDescription>
          </CardHeader>
          
          <CardContent>
            <Tabs value={activeTab} onValueChange={setActiveTab} className="w-full">
              <TabsList className="grid w-full grid-cols-2">
                <TabsTrigger value="login">Login</TabsTrigger>
                <TabsTrigger value="signup">Sign Up</TabsTrigger>
              </TabsList>
              
              <TabsContent value="login" className="space-y-4">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="login-email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-email"
                        type="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={handleInputChange('email')}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="login-password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="login-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Enter your password"
                        value={formData.password}
                        onChange={handleInputChange('password')}
                        className="pl-10 pr-10"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                  
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="text-sm text-destructive bg-destructive/10 p-3 rounded-md"
                    >
                      {error}
                    </motion.div>
                  )}
                  
                  <Button
                    type="submit"
                    className="w-full btn-nova"
                    disabled={!isFormValid() || isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Signing in...
                      </>
                    ) : (
                      'Sign In'
                    )}
                  </Button>
                </form>
              </TabsContent>
              
              <TabsContent value="signup" className="space-y-4">
                <form onSubmit={handleSubmit} className="space-y-4">
                  <div className="space-y-2">
                    <Label htmlFor="signup-email">Email</Label>
                    <div className="relative">
                      <Mail className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="signup-email"
                        type="email"
                        placeholder="Enter your email"
                        value={formData.email}
                        onChange={handleInputChange('email')}
                        className="pl-10"
                        required
                      />
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="signup-password">Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="signup-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Create a password"
                        value={formData.password}
                        onChange={handleInputChange('password')}
                        className="pl-10 pr-10"
                        required
                      />
                      <Button
                        type="button"
                        variant="ghost"
                        size="sm"
                        className="absolute right-0 top-0 h-full px-3 py-2 hover:bg-transparent"
                        onClick={() => setShowPassword(!showPassword)}
                      >
                        {showPassword ? <EyeOff className="h-4 w-4" /> : <Eye className="h-4 w-4" />}
                      </Button>
                    </div>
                  </div>
                  
                  <div className="space-y-2">
                    <Label htmlFor="confirm-password">Confirm Password</Label>
                    <div className="relative">
                      <Lock className="absolute left-3 top-3 h-4 w-4 text-muted-foreground" />
                      <Input
                        id="confirm-password"
                        type={showPassword ? 'text' : 'password'}
                        placeholder="Confirm your password"
                        value={formData.confirmPassword}
                        onChange={handleInputChange('confirmPassword')}
                        className="pl-10"
                        required
                      />
                    </div>
                    {formData.confirmPassword && formData.password !== formData.confirmPassword && (
                      <p className="text-sm text-destructive">Passwords do not match</p>
                    )}
                  </div>
                  
                  {error && (
                    <motion.div
                      initial={{ opacity: 0, height: 0 }}
                      animate={{ opacity: 1, height: 'auto' }}
                      className="text-sm text-destructive bg-destructive/10 p-3 rounded-md"
                    >
                      {error}
                    </motion.div>
                  )}
                  
                  <Button
                    type="submit"
                    className="w-full btn-nova"
                    disabled={!isFormValid() || isLoading}
                  >
                    {isLoading ? (
                      <>
                        <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                        Creating account...
                      </>
                    ) : (
                      <>
                        <UserPlus className="mr-2 h-4 w-4" />
                        Create Account
                      </>
                    )}
                  </Button>
                </form>
              </TabsContent>
            </Tabs>
            
            <div className="mt-6 text-center text-sm text-muted-foreground">
              <p>By continuing, you agree to our Terms of Service and Privacy Policy</p>
              {activeTab === 'signup' && (
                <p className="mt-2 text-primary">
                  After signup, you'll complete a quick profile setup to personalize your Nova experience.
                </p>
                )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}
