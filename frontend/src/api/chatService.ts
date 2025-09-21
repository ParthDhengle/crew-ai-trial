/**
 * Nova AI Assistant - Chat Service
 * 
 * Handles real-time chat communication with the backend
 * Manages message streaming, session state, and error handling
 */

import { apiClient, authManager } from './client';
import type { ChatMessage, ChatSession } from './types';

export interface ChatServiceCallbacks {
  onMessage?: (message: ChatMessage) => void;
  onTyping?: (isTyping: boolean) => void;
  onError?: (error: Error) => void;
  onSessionUpdate?: (session: ChatSession) => void;
}

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
    if (!authManager.isAuthenticated()) {
      throw new Error('User not authenticated');
    }

    if (this.isProcessing) {
      throw new Error('Another message is being processed');
    }

    this.isProcessing = true;
    this.currentSessionId = sessionId || this.currentSessionId || `session-${Date.now()}`;

    try {
      // Notify typing started
      this.callbacks.onTyping?.(true);

      // Create user message
      const userMessage: ChatMessage = {
        id: `user-${Date.now()}`,
        content,
        role: 'user',
        timestamp: Date.now(),
      };

      // Notify user message
      this.callbacks.onMessage?.(userMessage);

      // Send to backend and get response
      const backendResponse = await apiClient.sendMessage(content, this.currentSessionId);
      const displayContent = typeof backendResponse === 'object' 
        ? backendResponse.display_response || JSON.stringify(backendResponse)  // Fallback to stringified if no display_response
        : backendResponse;  // If it's already a string (edge case)

      // Create assistant message
      const assistantMessage: ChatMessage = {
    id: `assistant-${Date.now()}`,
    content: displayContent,
    role: 'assistant',
    timestamp: Date.now(),
    actions: [
      { type: 'accept_schedule', label: 'Schedule Follow-up', payload: {} },
      { type: 'run_operation', label: 'Analyze Further', payload: {} }
    ]
  };

      // Notify assistant message
      this.callbacks.onMessage?.(assistantMessage);

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

  // Create a new chat session
  createNewSession(): ChatSession {
    const sessionId = `session-${Date.now()}`;
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
