import { useEffect, useState, useCallback } from 'react';
import type {
  AgentOp,
  SchedulerTask,
  ChatSession,
  ChatMessage,
  Integration,
  NovaRole
} from '@/api/types';
import { apiClient } from '@/api/client';
import { useNova } from '@/context/NovaContext'; // FIXED: Import useNova for state/dispatch
/**
 * React hook wrapper for Electron API interactions
 * Provides typed access to window.api methods with React state management
 */
export const useElectronApi = () => {
  const [isElectron] = useState(() =>
    typeof window !== 'undefined' &&
    window.api &&
    typeof window.api === 'object'
  );
  // Enhanced fallback for when running in browser (development)
  const mockApi = {
    requestExpand: async () => {
      console.log('Mock: requestExpand');
      return { success: true };
    },
    requestMinimize: async () => {
      console.log('Mock: requestMinimize');
      return { success: true };
    },
    setAlwaysOnTop: (flag: boolean) => console.log('Mock: setAlwaysOnTop', flag),
    windowMinimize: async () => { // FIXED: Make async for consistency
      console.log('Mock: windowMinimize (switching to mini)');
      return { success: true };
    },
    windowMaximize: () => console.log('Mock: windowMaximize'),
    windowClose: () => console.log('Mock: windowClose'),
    miniClose: () => console.log('Mock: miniClose'),
    transcribeStart: async (sessionId: string) => console.log('Mock: transcribeStart', sessionId),
    transcribeStop: async (sessionId: string) => console.log('Mock: transcribeStop', sessionId),
    transcribeStream: (sessionId: string, cb: (text: string, partial: boolean) => void) => {
      console.log('Mock: transcribeStream', sessionId);
      // Simulate streaming transcript
      setTimeout(() => cb('Hello, this is a mock transcript...', true), 1000);
      setTimeout(() => cb('Hello, this is a mock transcript for testing.', false), 2000);
      return () => {};
    },
    onMessageStream: (cb: (message: ChatMessage) => void) => {
      console.log('Mock: onMessageStream');
      return () => {};
    },
    onAgentOpsUpdate: (cb: (ops: AgentOp[]) => void) => {
      console.log('Mock: onAgentOpsUpdate');
      return () => {};
    },
    executeAction: async (action: { type: string; payload?: unknown }) => ({ ok: true }),
    listLocalModels: async () => ['whisper-base', 'whisper-small', 'whisper-medium'],
    speak: async (text: string, voiceId?: string) => console.log('Mock: speak', text, voiceId),
    sendMessage: async (message: string, sessionId?: string) => ({ sessionId: sessionId || 'mock-session' }),
    notify: (title: string, body?: string) => console.log('Mock: notify', title, body),
  };
  const api = isElectron ? window.api : mockApi;
  console.log('HOOK: useElectronApi initialized, isElectron:', isElectron);
  return {
    api,
    isElectron,
  };
};
/**
 * Hook for managing window state with improved error handling
 */
export const useWindowControls = () => {
  const { api, isElectron } = useElectronApi();
  const [isExpanding, setIsExpanding] = useState(false);
  const contract = useCallback(async () => { // FIXED: Override to switch to mini
    try {
      if (isElectron) {
        // Switch to mini instead of taskbar minimize
        await api.requestMinimize?.();
        console.log('HOOK: Minimized to mini widget');
      } else {
        console.log('Mock: windowMinimize (switching to mini)');
      }
    } catch (error) {
      console.error('Failed to minimize window:', error);
    }
  }, [api, isElectron]);
  const minimize = useCallback(() => {
    try {
      api.windowMinimize?.(); // <- must be exposed from preload → main
      console.log('HOOK: Minimized to taskbar');
    } catch (error) {
      console.error('Failed to minimize window:', error);
    }
  }, [api]);
  const maximize = useCallback(() => {
    try {
      api.windowMaximize?.();
    } catch (error) {
      console.error('Failed to maximize window:', error);
    }
  }, [api]);
  const close = useCallback(() => {
    try {
      api.windowClose?.();
    } catch (error) {
      console.error('Failed to close window:', error);
    }
  }, [api]);
  const expand = useCallback(async () => {
    if (isExpanding) {
      console.log('HOOK: Expand already in progress, skipping...');
      return { success: false, error: 'Expand already in progress' };
    }
    setIsExpanding(true);
    console.log('HOOK: Calling api.requestExpand...');
    try {
      console.log('HOOK: About to await requestExpand...');
      const result = await api.requestExpand?.();
      console.log('HOOK: api.requestExpand succeeded:', result);
      // FIXED: Reset immediately on success
      setIsExpanding(false);
      // Add a small delay to ensure window switch completes
      await new Promise(resolve => setTimeout(resolve, 100));
      return result || { success: true };
    } catch (error) {
      console.error('HOOK: api.requestExpand failed:', error);
      // FIXED: Reset on error too
      setIsExpanding(false);
      return { success: false, error: error.message };
    }
  }, [api, isExpanding]);
  const miniClose = useCallback(() => {
    try {
      if (isElectron && api.miniClose) {
        api.miniClose();
      } else {
        api.windowClose?.();
      }
    } catch (error) {
      console.error('Failed to close mini window:', error);
    }
  }, [api, isElectron]);
  return {
    contract,
    minimize,
    maximize,
    close,
    expand,
    miniClose,
    isExpanding
  };
};
export const useVoiceTranscription = () => {
  const [isRecording, setIsRecording] = useState(false);
  const [transcript, setTranscript] = useState('');
  const [isPartial, setIsPartial] = useState(false);
  const { api } = useElectronApi();
  const startRecording = useCallback(async () => {
    const sessionId = `voice-${Date.now()}`;
    setIsRecording(true);
    setTranscript('');
    try {
      await api.transcribeStart(sessionId);
      // Set up streaming transcript
      api.transcribeStream(sessionId, (text: string, partial: boolean) => {
        setTranscript(text);
        setIsPartial(partial);
      });
    } catch (error) {
      console.error('Failed to start recording:', error);
      setIsRecording(false);
    }
  }, [api]);
  const stopRecording = useCallback(async () => {
    const sessionId = `voice-${Date.now()}`;
    setIsRecording(false);
    try {
      await api.transcribeStop(sessionId);
    } catch (error) {
      console.error('Failed to stop recording:', error);
    }
  }, [api]);
  return {
    isRecording,
    transcript,
    isPartial,
    startRecording,
    stopRecording,
  };
};