// frontend/src/api/chatService.ts
import { apiClient, authManager } from './client';
import type { ChatMessage, ChatSession } from './types';

export interface ChatServiceCallbacks {
  onMessage?: (message: ChatMessage) => void;
  onTyping?: (isTyping: boolean) => void;
  onError?: (error: Error) => void;
  onSessionUpdate?: (session: ChatSession) => void;
}
import { getAuth } from 'firebase/auth';

class ChatService {
  private callbacks: ChatServiceCallbacks = {};
  private currentSessionId: string | null = null;
  private isProcessing = false;

  // Set up callbacks
  setCallbacks(callbacks: ChatServiceCallbacks) {
    this.callbacks = { ...this.callbacks, ...callbacks };
  }

  // Send a message and get AI response
  async sendMessage(content: string, sessionId?: string): Promise<ChatMessage> {
    if (!getAuth().currentUser) {
      throw new Error('User not authenticated');
    }
    if (this.isProcessing) {
      throw new Error('Another message is being processed');
    }
    this.isProcessing = true;
    this.currentSessionId = sessionId || this.currentSessionId || `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;

    try {
      // Notify typing started
      this.callbacks.onTyping?.(true);

      // Create user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        content,
        role: 'user',
        timestamp: Date.now(),
      };

      // Notify user message
      this.callbacks.onMessage?.(userMessage);

      // Send to backend and get response
      const backendResponse = await apiClient.sendMessage(content, this.currentSessionId);

      // Extract nested result or flat response
      let displayContent: string;

      // If backend returned a JSON string, try to parse it
      let parsedResponse: any = backendResponse;
      if (typeof backendResponse === 'string') {
        try {
          parsedResponse = JSON.parse(backendResponse);
        } catch (e) {
          // If it can't be parsed, keep it as the raw string
          parsedResponse = backendResponse;
        }
      }

      // If parsedResponse has a 'result' object and it includes display_response, use it
      if (parsedResponse && typeof parsedResponse === 'object' && 'result' in parsedResponse && parsedResponse.result) {
        const result = parsedResponse.result;
        if (typeof result === 'object' && 'display_response' in result && result.display_response != null) {
          displayContent = String(result.display_response);
        } else {
          // If result exists but doesn't contain display_response, stringify the result object
          displayContent = typeof result === 'string' ? result : JSON.stringify(result, null, 2);
        }
      } else if (parsedResponse && typeof parsedResponse === 'object' && 'display_response' in parsedResponse) {
        // Flat response shape: { display_response: string, mode: string }
        displayContent = String(parsedResponse.display_response ?? '');
      } else {
        // Fallback: if parsedResponse is a primitive (string/number) use it, otherwise stringify
        displayContent = (typeof parsedResponse === 'string' || typeof parsedResponse === 'number')
          ? String(parsedResponse)
          : JSON.stringify(parsedResponse, null, 2);
      }
      // Update currentSessionId if backend returns a new one
      if (backendResponse.session_id) {
        this.currentSessionId = backendResponse.session_id;
      }

      // Create assistant message
      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}-${Math.random().toString(36).slice(2)}`,
        content: displayContent,
        role: 'assistant',
        timestamp: Date.now(),
        actions: [
          { type: 'accept_schedule', label: 'Schedule Follow-up', payload: {} },
          { type: 'run_operation', label: 'Analyze Further', payload: {} },
        ],
      };

      // Notify assistant message
      this.callbacks.onMessage?.(assistantMessage);

      // Fetch updated session after message to ensure real data
      if (this.currentSessionId) {
        const updatedSession = await this.getChatSession(this.currentSessionId);
        this.callbacks.onSessionUpdate?.(updatedSession);
      }

      return assistantMessage;
    } catch (error) {
      console.error('Chat service error:', error);
      this.callbacks.onError?.(error as Error);
      throw error;
    } finally {
      this.isProcessing = false;
      this.callbacks.onTyping?.(false);
    }
  }

  // Get chat history for a session
  async getChatHistory(sessionId?: string): Promise<ChatMessage[]> {
    try {
      return await apiClient.getChatHistory(sessionId);
    } catch (error) {
      console.error('Failed to get chat history:', error);
      this.callbacks.onError?.(error as Error);
      return [];
    }
  }

  // Get all chat sessions
  async getChatSessions(): Promise<ChatSession[]> {
    try {
      return await apiClient.getChatSessions();
    } catch (error) {
      console.error('Failed to get chat sessions:', error);
      this.callbacks.onError?.(error as Error);
      return [];
    }
  }

  // Fetch a single session with messages
  async getChatSession(sessionId: string): Promise<ChatSession> {
    try {
      const sessions = await apiClient.getChatSessions();
      const session: ChatSession | undefined = sessions.find((s) => s.id === sessionId);
      if (!session) {
        throw new Error('Session not found');
      }
      const history = await this.getChatHistory(sessionId);
      return { ...session, messages: history };
    } catch (error) {
      console.error('Failed to get chat session:', error);
      throw error;
    }
  }

  // Create a new chat session
  createNewSession(): ChatSession {
    const sessionId = `session-${Date.now()}-${Math.random().toString(36).slice(2)}`;
    const newSession: ChatSession = {
      id: sessionId,
      title: 'New Chat',
      summary: '',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };
    this.currentSessionId = sessionId;
    this.callbacks.onSessionUpdate?.(newSession);
    return newSession;
  }

  // Get current session ID
  getCurrentSessionId(): string | null {
    return this.currentSessionId;
  }

  // Set current session
  setCurrentSession(sessionId: string) {
    this.currentSessionId = sessionId;
  }

  // Check if currently processing
  isCurrentlyProcessing(): boolean {
    return this.isProcessing;
  }

  // Clear current session
  clearCurrentSession() {
    this.currentSessionId = null;
  }
}

// Create singleton instance
export const chatService = new ChatService();

// Export for use in components
export default chatService;