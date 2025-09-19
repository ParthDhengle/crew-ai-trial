import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  Settings as SettingsIcon,
  Mic,
  Mail,
  Calendar,
  Smartphone,
  Monitor,
  Shield,
  Info,
  ExternalLink,
  CheckCircle,
  AlertCircle,
  Loader2,
  Volume2,
  Bot,
  User
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Switch } from '@/components/ui/switch';
import { Label } from '@/components/ui/label';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { Badge } from '@/components/ui/badge';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
} from '@/components/ui/dialog';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Separator } from '@/components/ui/separator';
import { useNova } from '@/context/NovaContext';
import { useAuth } from '@/context/AuthContext';
import { useElectronApi } from '@/hooks/useElectronApi';

/**
 * Nova Settings - Configuration and integration management
 * 
 * Features:
 * - Voice settings (local Whisper model selection)
 * - Integration toggles (Email, Calendar, Smartwatch, Device Activity)
 * - OAuth setup flows
 * - Privacy controls
 * - Role preferences
 * - Model selection
 * - Connection status indicators
 * - Setup wizards for integrations
 */

interface IntegrationSetupProps {
  integration: {
    id: string;
    name: string;
    enabled: boolean;
    status: 'connected' | 'disconnected' | 'error';
    lastSync?: number;
  };
  onToggle: (enabled: boolean) => void;
  onSetup: () => void;
}

function IntegrationCard({ integration, onToggle, onSetup }: IntegrationSetupProps) {
  const [isConnecting, setIsConnecting] = useState(false);

  const getStatusIcon = () => {
    if (isConnecting) return <Loader2 size={16} className="animate-spin" />;
    
    switch (integration.status) {
      case 'connected':
        return <CheckCircle size={16} className="text-green-400" />;
      case 'error':
        return <AlertCircle size={16} className="text-red-400" />;
      default:
        return <AlertCircle size={16} className="text-muted-foreground" />;
    }
  };

  const getIcon = () => {
    switch (integration.id) {
      case 'email':
        return <Mail size={20} />;
      case 'calendar':
        return <Calendar size={20} />;
      case 'smartwatch':
        return <Smartphone size={20} />;
      case 'device':
        return <Monitor size={20} />;
      default:
        return <Shield size={20} />;
    }
  };

  const handleConnect = async () => {
    setIsConnecting(true);
    
    try {
      // TODO: IMPLEMENT IN PRELOAD - window.api.openExternalAuth(integration.id)
      await new Promise(resolve => setTimeout(resolve, 2000)); // Mock delay
      onSetup();
    } finally {
      setIsConnecting(false);
    }
  };

  return (
    <div className="card-nova p-4 flex items-center justify-between">
      <div className="flex items-center gap-3">
        <div className="text-primary">
          {getIcon()}
        </div>
        
        <div className="flex-1">
          <div className="flex items-center gap-2">
            <span className="font-medium">{integration.name}</span>
            {getStatusIcon()}
          </div>
          
          <div className="text-sm text-muted-foreground">
            {integration.status === 'connected' && integration.lastSync ? (
              <>Last synced {new Date(integration.lastSync).toLocaleString()}</>
            ) : integration.status === 'error' ? (
              'Connection error - needs reconfiguration'
            ) : (
              'Not connected'
            )}
          </div>
        </div>
      </div>

      <div className="flex items-center gap-2">
        {integration.enabled && integration.status !== 'connected' && (
          <Button
            size="sm"
            variant="outline"
            onClick={handleConnect}
            disabled={isConnecting}
            className="gap-2"
          >
            {isConnecting ? (
              <Loader2 size={12} className="animate-spin" />
            ) : (
              <ExternalLink size={12} />
            )}
            {isConnecting ? 'Connecting...' : 'Connect'}
          </Button>
        )}
        
        <Switch
          checked={integration.enabled}
          onCheckedChange={onToggle}
        />
      </div>
    </div>
  );
}

interface EmailSetupDialogProps {
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onComplete: () => void;
}

function EmailSetupDialog({ open, onOpenChange, onComplete }: EmailSetupDialogProps) {
  const [step, setStep] = useState(1);
  const [isConnecting, setIsConnecting] = useState(false);

  const handleConnect = async () => {
    setIsConnecting(true);
    
    // TODO: IMPLEMENT IN PRELOAD - window.api.openExternalAuth('email')
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    setStep(2);
    setIsConnecting(false);
  };

  const handleComplete = () => {
    // TODO: IMPLEMENT IN PRELOAD - window.api.enableIntegration('email', credentials)
    onComplete();
    onOpenChange(false);
    setStep(1);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>Connect Email</DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          {step === 1 && (
            <>
              <div className="text-center py-6">
                <Mail size={48} className="mx-auto mb-4 text-primary" />
                <h3 className="font-medium mb-2">Email Integration Setup</h3>
                <p className="text-sm text-muted-foreground">
                  Connect your email to enable smart categorization, automated responses, 
                  and priority sorting powered by Nova AI.
                </p>
              </div>
              
              <div className="space-y-3">
                <div className="flex items-start gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-primary/10 text-primary flex items-center justify-center text-xs font-bold mt-0.5">
                    1
                  </div>
                  <div>
                    <div className="font-medium">Secure OAuth Connection</div>
                    <div className="text-muted-foreground">
                      We'll open your browser to authenticate with your email provider
                    </div>
                  </div>
                </div>
                
                <div className="flex items-start gap-3 text-sm">
                  <div className="w-5 h-5 rounded-full bg-muted text-muted-foreground flex items-center justify-center text-xs font-bold mt-0.5">
                    2
                  </div>
                  <div>
                    <div className="font-medium">Grant Permissions</div>
                    <div className="text-muted-foreground">
                      Allow Nova to read and organize your emails locally
                    </div>
                  </div>
                </div>
              </div>

              <Button 
                onClick={handleConnect} 
                className="w-full btn-nova gap-2"
                disabled={isConnecting}
              >
                {isConnecting ? (
                  <>
                    <Loader2 size={16} className="animate-spin" />
                    Opening browser...
                  </>
                ) : (
                  <>
                    <ExternalLink size={16} />
                    Connect Email Account
                  </>
                )}
              </Button>
            </>
          )}

          {step === 2 && (
            <>
              <div className="text-center py-6">
                <CheckCircle size={48} className="mx-auto mb-4 text-green-400" />
                <h3 className="font-medium mb-2">Connection Successful!</h3>
                <p className="text-sm text-muted-foreground">
                  Your email has been connected successfully. Nova can now help you 
                  manage your inbox with AI-powered organization.
                </p>
              </div>

              <Button onClick={handleComplete} className="w-full btn-nova">
                Complete Setup
              </Button>
            </>
          )}
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function Settings() {
  const { state, dispatch } = useNova();
  const { logout } = useAuth();
  const { api } = useElectronApi();
  const [localModels, setLocalModels] = useState(['whisper-base', 'whisper-small', 'whisper-medium']);
  const [showEmailSetup, setShowEmailSetup] = useState(false);

  // Handle integration toggle
  const handleIntegrationToggle = (integrationId: string, enabled: boolean) => {
    const updatedIntegrations = state.integrations.map(integration =>
      integration.id === integrationId 
        ? { ...integration, enabled }
        : integration
    );
    
    dispatch({ type: 'SET_INTEGRATIONS', payload: updatedIntegrations });
    
    if (enabled && integrationId === 'email') {
      setShowEmailSetup(true);
    }
  };

  // Handle integration setup completion
  const handleIntegrationSetup = (integrationId: string) => {
    const updatedIntegrations = state.integrations.map(integration =>
      integration.id === integrationId 
        ? { ...integration, status: 'connected' as const, lastSync: Date.now() }
        : integration
    );
    
    dispatch({ type: 'SET_INTEGRATIONS', payload: updatedIntegrations });
  };

  // Handle model selection
  const handleModelChange = (model: string) => { // Fixed: Specific string type
    dispatch({ type: 'SET_VOICE_ENABLED', payload: true });
    // TODO: IMPLEMENT IN PRELOAD - window.api.updateUserPreferences({ selectedModel: model })
    console.log('Selected model:', model);
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center gap-3">
          <SettingsIcon size={24} className="text-primary" />
          <div>
            <h1 className="text-2xl font-bold">Settings</h1>
            <p className="text-muted-foreground">
              Configure Nova's behavior and integrations
            </p>
          </div>
        </div>
      </div>

      {/* Settings Content */}
      <ScrollArea className="flex-1">
        <div className="max-w-2xl mx-auto p-6 space-y-8">
          
          {/* Voice Settings */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Mic size={20} className="text-primary" />
              <h2 className="text-lg font-semibold">Voice & Speech</h2>
            </div>
            
            <div className="space-y-4">
              <div className="flex items-center justify-between">
                <div className="space-y-1">
                  <Label>Enable Voice Input</Label>
                  <p className="text-sm text-muted-foreground">
                    Use local Whisper for speech-to-text conversion
                  </p>
                </div>
                <Switch
                  checked={state.voiceEnabled}
                  onCheckedChange={(checked) => dispatch({ type: 'SET_VOICE_ENABLED', payload: checked })}
                />
              </div>

              {state.voiceEnabled && (
                <div className="space-y-2">
                  <Label>Local Whisper Model</Label>
                  <Select value={state.selectedModel} onValueChange={handleModelChange}>
                    <SelectTrigger>
                      <SelectValue />
                    </SelectTrigger>
                    <SelectContent>
                      <SelectItem value="whisper-base">
                        <div className="flex flex-col">
                          <span>Whisper Base</span>
                          <span className="text-xs text-muted-foreground">Fast, good quality</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="whisper-small">
                        <div className="flex flex-col">
                          <span>Whisper Small</span>
                          <span className="text-xs text-muted-foreground">Balanced speed and accuracy</span>
                        </div>
                      </SelectItem>
                      <SelectItem value="whisper-medium">
                        <div className="flex flex-col">
                          <span>Whisper Medium</span>
                          <span className="text-xs text-muted-foreground">High accuracy, slower</span>
                        </div>
                      </SelectItem>
                    </SelectContent>
                  </Select>
                  
                  <div className="flex items-center gap-2 mt-2">
                    <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">
                      Local Processing
                    </Badge>
                    <span className="text-xs text-muted-foreground">
                      All voice processing happens on your device
                    </span>
                  </div>
                </div>
              )}
            </div>
          </section>

          <Separator />

          {/* Role Settings */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Bot size={20} className="text-primary" />
              <h2 className="text-lg font-semibold">AI Personality</h2>
            </div>
            
            <div className="space-y-2">
              <Label>Nova's Role</Label>
              <Select value={state.role} onValueChange={(value: NovaRole) => dispatch({ type: 'SET_ROLE', payload: value })}>
                <SelectTrigger>
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="friend">Friend - Casual and supportive</SelectItem>
                  <SelectItem value="mentor">Mentor - Guidance and wisdom</SelectItem>
                  <SelectItem value="girlfriend">Girlfriend - Loving and caring</SelectItem>
                  <SelectItem value="husband">Husband - Protective and reliable</SelectItem>
                  <SelectItem value="guide">Guide - Professional assistant</SelectItem>
                </SelectContent>
              </Select>
              
              <p className="text-sm text-muted-foreground">
                This affects Nova's conversation tone and approach
              </p>
            </div>
          </section>

          <Separator />

          {/* Integrations */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Shield size={20} className="text-primary" />
              <h2 className="text-lg font-semibold">Integrations</h2>
            </div>
            
            <div className="space-y-3">
              {state.integrations.map((integration) => (
                <IntegrationCard
                  key={integration.id}
                  integration={integration}
                  onToggle={(enabled) => handleIntegrationToggle(integration.id, enabled)}
                  onSetup={() => handleIntegrationSetup(integration.id)}
                />
              ))}
            </div>

            <div className="p-4 rounded-lg bg-muted/20 border border-muted">
              <div className="flex items-start gap-3">
                <Info size={16} className="text-primary mt-0.5" />
                <div className="text-sm">
                  <div className="font-medium mb-1">Privacy First</div>
                  <div className="text-muted-foreground">
                    All data processing happens locally. Integrations only sync necessary 
                    information and respect your privacy preferences.
                  </div>
                </div>
              </div>
            </div>
          </section>

          <Separator />

          {/* Privacy & Security */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <Shield size={20} className="text-primary" />
              <h2 className="text-lg font-semibold">Privacy & Security</h2>
            </div>
            
            <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
              <div className="p-4 rounded-lg bg-green-500/5 border border-green-500/20">
                <div className="flex items-center gap-2 mb-2">
                  <CheckCircle size={16} className="text-green-400" />
                  <span className="font-medium text-sm">Local Processing</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  All AI computations run on your device
                </p>
              </div>
              
              <div className="p-4 rounded-lg bg-primary/5 border border-primary/20">
                <div className="flex items-center gap-2 mb-2">
                  <Shield size={16} className="text-primary" />
                  <span className="font-medium text-sm">Encrypted Storage</span>
                </div>
                <p className="text-xs text-muted-foreground">
                  Your data is encrypted at rest
                </p>
              </div>
            </div>
          </section>

          <Separator />

          {/* Account */}
          <section className="space-y-4">
            <div className="flex items-center gap-2">
              <User size={20} className="text-primary" />
              <h2 className="text-lg font-semibold">Account</h2>
            </div>
            
            <div className="space-y-4">
              <div className="p-4 rounded-lg bg-muted/20 border border-muted">
                <div className="flex items-center justify-between">
                  <div>
                    <div className="font-medium">Sign Out</div>
                    <div className="text-sm text-muted-foreground">
                      Sign out of your Nova account
                    </div>
                  </div>
                  <Button
                    variant="outline"
                    onClick={logout}
                    className="text-destructive hover:text-destructive hover:bg-destructive/10"
                  >
                    Sign Out
                  </Button>
                </div>
              </div>
            </div>
          </section>
        </div>
      </ScrollArea>

      {/* Email Setup Dialog */}
      <EmailSetupDialog
        open={showEmailSetup}
        onOpenChange={setShowEmailSetup}
        onComplete={() => handleIntegrationSetup('email')}
      />
    </div>
  );
}