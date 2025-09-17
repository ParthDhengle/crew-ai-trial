// Make sure React knows about custom CSS properties
import 'react';

declare module 'react' {
  interface CSSProperties {
    ['-webkit-app-region']?: 'drag' | 'no-drag';
  }
}

// Extend the global Window object with Electron API
export {};

declare global {
  interface Window {
    api: {
      // Window control
      requestExpand(): Promise<{ success: boolean }>;
      requestMinimize(): Promise<{ success: boolean }>;
      setAlwaysOnTop(flag: boolean): void;
      windowMinimize(): void;
      windowMaximize(): void;
      windowClose(): void;
      miniClose(): void; // ✅ NEW FIX

      // Voice / Local Whisper
      transcribeStart(sessionId: string): Promise<void>;
      transcribeStop(sessionId: string): Promise<void>;
      transcribeStream(
        sessionId: string,
        onTranscript: (text: string, partial: boolean) => void
      ): () => void;
      listLocalModels(): Promise<string[]>;

      // TTS
      speak(text: string, voiceId?: string): Promise<void>;

      // Chat & AI
      sendMessage(
        message: string,
        sessionId?: string
      ): Promise<{ sessionId: string }>;
      onMessageStream(cb: (message: unknown) => void): () => void;

      // Agent Ops
      executeAction(action: { type: string; payload?: unknown }): Promise<{ ok: boolean }>;
      onAgentOpsUpdate(cb: (ops: unknown[]) => void): () => void;

      // Preferences, integrations, etc...
      getAppVersion(): Promise<string>;
      notify(title: string, body?: string): void;
    };
  }
}
