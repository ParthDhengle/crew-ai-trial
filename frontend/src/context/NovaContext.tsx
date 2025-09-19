// frontend/src/context/NovaContext.tsx (complete with fixes)
import React, { createContext, useReducer, useContext, ReactNode, useEffect } from 'react';
import { useAuth } from '@/hooks/useAuth';
import { collection, query, orderBy, onSnapshot } from 'firebase/firestore';
import { db } from '@/firebase';
import type { AgentOp, SchedulerTask, ChatMessage, ChatSession, Integration, NovaRole } from '@/api/types';

type NovaAction =
  | { type: 'SET_VIEW'; payload: 'chat' | 'scheduler' | 'dashboard' | 'settings' }
  | { type: 'SET_ROLE'; payload: NovaRole }
  | { type: 'SET_VOICE_ENABLED'; payload: boolean }
  | { type: 'SET_SELECTED_MODEL'; payload: string }
  | { type: 'SET_ALWAYS_ON_TOP'; payload: boolean }
  | { type: 'SET_SIDEBAR_COLLAPSED'; payload: boolean }
  | { type: 'SET_CURRENT_SESSION'; payload: ChatSession | null }
  | { type: 'SET_SESSIONS'; payload: ChatSession[] }
  | { type: "ADD_SESSION"; payload: ChatSession }
  | { type: 'ADD_MESSAGE'; payload: { sessionId: string; message: ChatMessage } }
  | { type: 'SET_MESSAGES'; payload: { sessionId: string; messages: ChatMessage[] } }
  | { type: 'SET_TYPING'; payload: boolean }
  | { type: 'SET_TASKS'; payload: SchedulerTask[] }
  | { type: 'ADD_TASK'; payload: SchedulerTask }
  | { type: 'UPDATE_TASK'; payload: { id: string; updates: Partial<SchedulerTask> } }
  | { type: 'DELETE_TASK'; payload: string }
  | { type: 'SET_OPERATIONS'; payload: AgentOp[] }
  | { type: 'SET_INTEGRATIONS'; payload: Integration[] }
  | { type: 'SET_MINI_MODE'; payload: boolean }
  | { type: 'SET_DRAFT'; payload: string };

interface NovaState {
  view: 'chat' | 'scheduler' | 'dashboard' | 'settings';
  role: NovaRole;
  voiceEnabled: boolean;
  selectedModel: string;
  alwaysOnTop: boolean;
  sidebarCollapsed: boolean;
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  isTyping: boolean;
  tasks: SchedulerTask[];
  operations: AgentOp[];
  integrations: Integration[];
  isMiniMode: boolean;
  draftMessage: string;
}

const initialState: NovaState = {
  view: 'chat',
  role: 'guide',
  voiceEnabled: true,
  selectedModel: 'whisper-base',
  alwaysOnTop: false,
  sidebarCollapsed: false,
  currentSession: null,
  sessions: [],
  isTyping: false,
  tasks: [],
  operations: [],
  integrations: [],
  isMiniMode: false,
  draftMessage: '',
};

const NovaContext = createContext<{
  state: NovaState;
  dispatch: React.Dispatch<NovaAction>;
} | null>(null);

export const NovaProvider = ({ children }: { children: ReactNode }) => {
  const [state, dispatch] = useReducer((state: NovaState, action: NovaAction) => {
    switch (action.type) {
      case 'SET_VIEW':
        return { ...state, view: action.payload };
      case 'SET_ROLE':
        return { ...state, role: action.payload };
      case 'SET_VOICE_ENABLED':
        return { ...state, voiceEnabled: action.payload };
      case 'SET_SELECTED_MODEL':
        return { ...state, selectedModel: action.payload };
      case 'SET_ALWAYS_ON_TOP':
        return { ...state, alwaysOnTop: action.payload };
      case 'SET_SIDEBAR_COLLAPSED':
        return { ...state, sidebarCollapsed: action.payload };
      case 'SET_CURRENT_SESSION':
        return { ...state, currentSession: action.payload };
      case 'SET_SESSIONS':
        return { ...state, sessions: action.payload };
      case 'ADD_SESSION':
        return {
          ...state,
          sessions: [...state.sessions, action.payload],
          currentSession: action.payload,
        };
      case 'ADD_MESSAGE':
        if (state.currentSession?.id === action.payload.sessionId) {
          const updatedSession = {
            ...state.currentSession,
            messages: [...state.currentSession.messages, action.payload.message],
            updatedAt: Date.now(),
          };
          return {
            ...state,
            currentSession: updatedSession,
            sessions: state.sessions.map(s => s.id === action.payload.sessionId ? updatedSession : s),
          };
        }
        return state;
      case 'SET_MESSAGES':
        if (state.currentSession?.id === action.payload.sessionId) {
          return { ...state, currentSession: { ...state.currentSession, messages: action.payload.messages } };
        }
        return state;
      case 'SET_TYPING':
        return { ...state, isTyping: action.payload };
      case 'SET_TASKS':
        return { ...state, tasks: action.payload };
      case 'ADD_TASK':
        return { ...state, tasks: [...state.tasks, action.payload] };
      case 'UPDATE_TASK':
        return {
          ...state,
          tasks: state.tasks.map(t => t.id === action.payload.id ? { ...t, ...action.payload.updates } : t),
        };
      case 'DELETE_TASK':
        return { ...state, tasks: state.tasks.filter(t => t.id !== action.payload) };
      case 'SET_OPERATIONS':
        return { ...state, operations: action.payload };
      case 'SET_INTEGRATIONS':
        return { ...state, integrations: action.payload };
      case 'SET_MINI_MODE':
        return { ...state, isMiniMode: action.payload };
      case 'SET_DRAFT':
        return { ...state, draftMessage: action.payload };
      default:
        return state;
    }
  }, initialState);

  const { user, profile, updateUserProfile } = useAuth();

  useEffect(() => {
    if (profile && !state.currentSession) {
      let sessionId = profile.current_chat_session;
      if (!sessionId) {
        sessionId = crypto.randomUUID();
        updateUserProfile({ current_chat_session: sessionId });
      }
      dispatch({ type: 'SET_CURRENT_SESSION', payload: { 
        id: sessionId, 
        title: 'Main Chat', 
        messages: [], 
        createdAt: Date.now(), 
        updatedAt: Date.now() 
      } });
      const q = query(collection(db, 'chats', sessionId, 'messages'), orderBy('timestamp'));
      onSnapshot(q, (snap) => {
        const msgs = snap.docs.map(doc => ({
          id: doc.id,
          ...doc.data(),
          timestamp: doc.data().timestamp?.toDate().getTime() || Date.now()
        } as ChatMessage));
        dispatch({ type: 'SET_MESSAGES', payload: { sessionId, messages: msgs } });
      });
    }
  }, [profile]);

  useEffect(() => {
    if (profile) {
      dispatch({ type: 'SET_ROLE', payload: profile.role });
      dispatch({ type: 'SET_VOICE_ENABLED', payload: profile.voiceEnabled });
      dispatch({ type: 'SET_SELECTED_MODEL', payload: profile.selectedModel });
      dispatch({ type: 'SET_ALWAYS_ON_TOP', payload: profile.alwaysOnTop });
    }
  }, [profile]);

  return (
    <NovaContext.Provider value={{ state, dispatch }}>
      {children}
    </NovaContext.Provider>
  );
};

export const useNova = () => {
  const context = useContext(NovaContext);
  if (!context) {
    throw new Error('useNova must be used within NovaProvider');
  }
  return context;
};