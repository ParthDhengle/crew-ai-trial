/**
 * Nova AI Assistant - Electron API Type Definitions
 * 
 * This file defines the TypeScript interface for the Electron preload API
 * that the React UI will interact with. All window.api methods must be
 * implemented in the Electron main/preload processes.
 */

export type AgentOp = {
  id: string;
  title: string;
  desc?: string;
  status: 'pending' | 'running' | 'success' | 'failed';
  progress?: number;
  startTime?: number;
  endTime?: number;
  result?: string;
};

export type SchedulerTask = {
  id: string;
  title: string;
  description: string;
  deadline: string; // ISO date string
  priority: 'High' | 'Medium' | 'Low';
  status: 'todo' | 'inprogress' | 'done';
  tags?: string[];
  isAgenticTask?: boolean;
  createdAt: string;
  updatedAt: string;
};

export type ChatMessage = {
  id: string;
  content: string;
  role: 'user' | 'assistant' | 'system';
  timestamp: number;
  actions?: MessageAction[];
  isStreaming?: boolean;
};

export type MessageAction = {
  type: 'accept_schedule' | 'reschedule' | 'send_email' | 'run_operation';
  label: string;
  payload?: unknown; // Fixed: Changed from any
};

export type ChatSession = {
  id: string;
  title: string;
  summary?: string;
  messages: ChatMessage[];
  createdAt: number;
  updatedAt: number;
};

export type NovaRole = 'friend' | 'mentor' | 'girlfriend' | 'husband' | 'guide';

export type Integration = {
  id: string;
  name: string;
  enabled: boolean;
  status: 'connected' | 'disconnected' | 'error';
  lastSync?: number;
};

export type Unsubscribe = () => void;

/**
 * Global Electron API interface - implemented in preload.js
 */
declare global {
  interface Window {
    api: {
      // Window control
      requestExpand(): void;
      requestMinimize(): void;
      setAlwaysOnTop(flag: boolean): void;
      windowMinimize(): void; // NEW: Minimize the window
      windowMaximize(): void; // NEW: Maximize/restore the window
      windowClose(): void; // NEW: Close the app
      miniClose(): void; // NEW: Close mini mode window
      // Voice / Local Whisper
      transcribeStart(sessionId: string): Promise<void>;
      transcribeStop(sessionId: string): Promise<void>;
      transcribeStream(sessionId: string, onTranscript: (text: string, partial: boolean) => void): void;
      listLocalModels(): Promise<string[]>;

      // TTS (only on user request)
      speak(text: string, voiceId?: string): Promise<void>;

      // Chat & AI
      sendMessage(message: string, sessionId?: string): Promise<{ sessionId: string }>;
      onMessageStream(cb: (message: ChatMessage) => void): Unsubscribe;
      
      // Agentic operations
      executeAction(action: { type: string; payload?: unknown }): Promise<{ ok: boolean }>; // Fixed: payload unknown
      onAgentOpsUpdate(cb: (ops: AgentOp[]) => void): Unsubscribe;

      // Scheduler
      createTask(task: Omit<SchedulerTask, 'id' | 'createdAt' | 'updatedAt'>): Promise<SchedulerTask>;
      updateTask(id: string, updates: Partial<SchedulerTask>): Promise<SchedulerTask>;
      deleteTask(id: string): Promise<void>;
      getTasks(): Promise<SchedulerTask[]>;

      // Chat sessions
      getChatSessions(): Promise<ChatSession[]>;
      getChatSession(id: string): Promise<ChatSession>;
      deleteChatSession(id: string): Promise<void>;
      searchChats(query: string): Promise<ChatSession[]>;

      // Integrations
      openExternalAuth(service: 'email' | 'google' | 'calendar'): Promise<void>;
      enableIntegration(service: string, credentials: unknown): Promise<{ ok: boolean }>; // Fixed: credentials unknown
      getIntegrations(): Promise<Integration[]>;

      // Exports
      exportDashboardPDF(payload: { html: string }): Promise<{ path: string }>;

      // Settings & preferences
      getUserPreferences(): Promise<{
        role: NovaRole;
        voiceEnabled: boolean;
        selectedModel: string;
        alwaysOnTop: boolean;
      }>;
      updateUserPreferences(prefs: unknown): Promise<void>; // Fixed: prefs unknown

      // Misc
      notify(title: string, body?: string): void;
      onThemeChange(cb: (theme: 'dark' | 'light') => void): Unsubscribe;
      getAppVersion(): Promise<string>;
    };
  }
}