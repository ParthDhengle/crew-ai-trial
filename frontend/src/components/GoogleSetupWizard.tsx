import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { Upload, CheckCircle, AlertCircle, Loader2 } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { apiClient } from '@/api/client';
import { useAuth } from '@/context/AuthContext';

const GoogleSetupWizard = ({ onSuccess }: { onSuccess?: () => void }) => {
  const { user } = useAuth();
  const [step, setStep] = useState(1);
  const [file, setFile] = useState<File | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [isLoading, setIsLoading] = useState(false);
  const [clientId, setClientId] = useState('');

  const handleFileChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    const selectedFile = e.target.files?.[0];
    if (selectedFile && selectedFile.type === 'application/json') {
      setFile(selectedFile);
      setError(null);
    } else {
      setError('Please upload a valid JSON file');
    }
  };

  const handleUpload = async () => {
    if (!file) return;
    setIsLoading(true);
    setError(null);
    
    try {
      const text = await file.text();
      const json = JSON.parse(text);
      const creds = json.web || json.installed;
      
      if (!creds?.client_id || !creds?.client_secret) {
        throw new Error('Invalid client secret format');
      }
      
      await apiClient.uploadClientSecret({
        client_id: creds.client_id,
        client_secret: creds.client_secret
      });
      
      setClientId(creds.client_id);
      setStep(2);
    } catch (err) {
      setError(err.message || 'Failed to process client secret');
    } finally {
      setIsLoading(false);
    }
  };

  const handleOAuth = () => {
    setIsLoading(true);
    setError(null);
    
    if (!window.google) {
      setError('Google API not loaded');
      setIsLoading(false);
      return;
    }
    
    const client = window.google.accounts.oauth2.initCodeClient({
      client_id: clientId,
      scope: 'https://www.googleapis.com/auth/calendar https://www.googleapis.com/auth/tasks',
      ux_mode: 'popup',
      callback: async (response: any) => {
        if (response.error) {
          setError(`OAuth failed: ${response.error}`);
          setIsLoading(false);
          return;
        }
        
        try {
          await apiClient.completeOAuth(response.code);
          onSuccess?.();
        } catch (err) {
          setError(err.message || 'Failed to complete setup');
        } finally {
          setIsLoading(false);
        }
      },
    });
    
    client.requestCode();
  };

  return (
    <Card className="w-full max-w-md mx-auto">
      <CardHeader>
        <CardTitle>Connect Google Calendar</CardTitle>
        <CardDescription>Upload your client secret JSON to connect</CardDescription>
      </CardHeader>
      <CardContent className="space-y-4">
        {step === 1 ? (
          <>
            <div className="space-y-2">
              <Label htmlFor="secret-file">Client Secret JSON</Label>
              <Input
                id="secret-file"
                type="file"
                accept=".json"
                onChange={handleFileChange}
              />
            </div>
            
            {error && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
            
            <Button 
              onClick={handleUpload} 
              disabled={!file || isLoading}
              className="w-full"
            >
              {isLoading ? <Loader2 className="mr-2 animate-spin" /> : <Upload className="mr-2" />}
              Upload and Proceed
            </Button>
          </>
        ) : (
          <>
            <div className="space-y-4 text-center">
              <CheckCircle className="mx-auto h-8 w-8 text-green-500" />
              <p>Client secret uploaded successfully.</p>
              <p>Now authorize access to your Google account.</p>
            </div>
            
            {error && (
              <div className="flex items-center gap-2 text-destructive">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}
            
            <Button 
              onClick={handleOAuth}
              disabled={isLoading}
              className="w-full"
            >
              {isLoading ? <Loader2 className="mr-2 animate-spin" /> : null}
              Authorize Google
            </Button>
          </>
        )}
      </CardContent>
    </Card>
  );
};

export default GoogleSetupWizard;