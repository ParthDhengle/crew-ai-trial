// frontend/src/context/NovaContext.tsx
import React, { createContext, useContext, useReducer, useEffect } from 'react';
import { useAuth, UserProfile } from '@/hooks/useAuth';
import { collection, onSnapshot, query, where, orderBy, addDoc, serverTimestamp } from 'firebase/firestore';
import { db } from '../firebase';
import axios from 'axios';
import type { ChatMessage, ChatSession, SchedulerTask, AgentOp, Integration, NovaRole } from '@/api/types';

interface NovaState {
  view: 'chat' | 'scheduler' | 'dashboard' | 'settings';
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  messages: ChatMessage[];  // For current session
  tasks: SchedulerTask[];
  operations: AgentOp[];
  integrations: Integration[];
  role: NovaRole;
  voiceEnabled: boolean;
  selectedModel: string;
  alwaysOnTop: boolean;
  sidebarCollapsed: boolean;
  isTyping: boolean;
}

type NovaAction =
  | { type: 'SET_VIEW'; payload: NovaState['view'] }
  | { type: 'SET_CURRENT_SESSION'; payload: ChatSession | null }
  | { type: 'SET_SESSIONS'; payload: ChatSession[] }
  | { type: 'ADD_MESSAGE'; payload: { sessionId: string; message: ChatMessage } }
  | { type: 'SET_MESSAGES'; payload: ChatMessage[] }
  | { type: 'SET_TASKS'; payload: SchedulerTask[] }
  | { type: 'ADD_TASK'; payload: SchedulerTask }
  | { type: 'UPDATE_TASK'; payload: { id: string; updates: Partial<SchedulerTask> } }
  | { type: 'DELETE_TASK'; payload: string }
  | { type: 'SET_OPERATIONS'; payload: AgentOp[] }
  | { type: 'SET_INTEGRATIONS'; payload: Integration[] }
  | { type: 'SET_ROLE'; payload: NovaRole }
  | { type: 'SET_VOICE_ENABLED'; payload: boolean }
  | { type: 'SET_SELECTED_MODEL'; payload: string }
  | { type: 'SET_ALWAYS_ON_TOP'; payload: boolean }
  | { type: 'SET_SIDEBAR_COLLAPSED'; payload: boolean }
  | { type: 'SET_TYPING'; payload: boolean };

const initialState: NovaState = {
  view: 'chat',
  currentSession: null,
  sessions: [],
  messages: [],
  tasks: [],
  operations: [],
  integrations: [],
  role: 'guide',
  voiceEnabled: true,
  selectedModel: 'whisper-base',
  alwaysOnTop: false,
  sidebarCollapsed: false,
  isTyping: false,
};

const novaReducer = (state: NovaState, action: NovaAction): NovaState => {
  switch (action.type) {
    case 'SET_VIEW':
      return { ...state, view: action.payload };
    case 'SET_CURRENT_SESSION':
      return { ...state, currentSession: action.payload };
    case 'SET_SESSIONS':
      return { ...state, sessions: action.payload };
    case 'ADD_MESSAGE':
      if (state.currentSession?.id === action.payload.sessionId) {
        return { ...state, messages: [...state.messages, action.payload.message] };
      }
      return state;
    case 'SET_MESSAGES':
      return { ...state, messages: action.payload };
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
    case 'SET_TYPING':
      return { ...state, isTyping: action.payload };
    default:
      return state;
  }
};

interface NovaContextType {
  state: NovaState;
  dispatch: React.Dispatch<NovaAction>;
  sendMessage: (message: string, sessionId?: string) => Promise<void>;
  createTask: (task: Omit<SchedulerTask, 'id' | 'createdAt' | 'updatedAt'>) => Promise<void>;
  updateTask: (id: string, updates: Partial<SchedulerTask>) => Promise<void>;
  deleteTask: (id: string) => Promise<void>;
  // Add more as needed
}

const NovaContext = createContext<NovaContextType | undefined>(undefined);

export const NovaProvider: React.FC<{ children: React.ReactNode }> = ({ children }) => {
  const [state, dispatch] = useReducer(novaReducer, initialState);
  const { profile, idToken, loading } = useAuth();

  // Sync profile to state on load
  useEffect(() => {
    if (profile && !loading) {
      dispatch({ type: 'SET_ROLE', payload: profile.role });
      dispatch({ type: 'SET_VOICE_ENABLED', payload: profile.voiceEnabled });
      dispatch({ type: 'SET_SELECTED_MODEL', payload: profile.selectedModel });
      dispatch({ type: 'SET_ALWAYS_ON_TOP', payload: profile.alwaysOnTop });
    }
  }, [profile, loading]);

  // Real-time listeners
  useEffect(() => {
    if (!idToken || loading) return;

    // Listen to tasks
    const tasksQuery = query(collection(db, 'tasks'), where('owner_id', '==', profile?.uid));
    const unsubscribeTasks = onSnapshot(tasksQuery, (snap) => {
      const tasksData = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as SchedulerTask));
      dispatch({ type: 'SET_TASKS', payload: tasksData });
    });

    // Listen to operations
    const opsQuery = query(collection(db, 'operations_queue'), where('user_id', '==', profile?.uid));
    const unsubscribeOps = onSnapshot(opsQuery, (snap) => {
      const opsData = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as AgentOp));
      dispatch({ type: 'SET_OPERATIONS', payload: opsData });
    });

    // Listen to chat sessions (group by session_id)
    const messagesQuery = query(collection(db, 'chat_history'), where('user_id', '==', profile?.uid), orderBy('timestamp'));
    const unsubscribeMessages = onSnapshot(messagesQuery, (snap) => {
      const allMessages = snap.docs.map(doc => ({ id: doc.id, ...doc.data() } as ChatMessage));
      // Group into sessions (simple: last 20 as current, others as history)
      const currentMessages = allMessages.slice(-20);
      dispatch({ type: 'SET_MESSAGES', payload: currentMessages });
      // Derive sessions (mock simple grouping; enhance with aggregation)
      const sessions = allMessages.reduce((acc: ChatSession[], msg, idx) => {
        if (idx % 10 === 0) {  // Every 10 msgs a "session"
          acc.push({ id: `sess-${idx}`, title: `Chat ${idx/10 +1}`, messages: [msg], createdAt: Date.now(), updatedAt: Date.now() });
        }
        return acc;
      }, []);
      dispatch({ type: 'SET_SESSIONS', payload: sessions });
    });

    return () => {
      unsubscribeTasks();
      unsubscribeOps();
      unsubscribeMessages();
    };
  }, [idToken, profile?.uid, loading]);

  // Send message to backend
  const sendMessage = async (message: string, sessionId?: string) => {
    if (!idToken) throw new Error('Not authenticated');
    dispatch({ type: 'SET_TYPING', payload: true });
    try {
      const response = await axios.post('http://127.0.0.1:8000/process_query', 
        { query: message, session_id: sessionId },
        { headers: { Authorization: `Bearer ${idToken}` } }
      );
      const aiResponse: ChatMessage = {
        id: `ai-${Date.now()}`,
        content: response.data.result,
        role: 'assistant',
        timestamp: Date.now(),
      };
      // Save to Firestore (client-side)
      await addDoc(collection(db, 'chat_history'), {
        ...aiResponse,
        user_id: profile?.uid,
        session_id: sessionId || 'default',
        timestamp: serverTimestamp(),
      });
    } catch (error) {
      console.error('Send message failed:', error);
    } finally {
      dispatch({ type: 'SET_TYPING', payload: false });
    }
  };

  // Task CRUD (via backend API)
  const createTask = async (task: Omit<SchedulerTask, 'id' | 'createdAt' | 'updatedAt'>) => {
    if (!idToken) throw new Error('Not authenticated');
    try {
      const response = await axios.post('http://127.0.0.1:8000/tasks', task, 
        { headers: { Authorization: `Bearer ${idToken}` } }
      );
      // Listener will update state
    } catch (error) {
      console.error('Create task failed:', error);
    }
  };

  const updateTask = async (id: string, updates: Partial<SchedulerTask>) => {
    if (!idToken) throw new Error('Not authenticated');
    try {
      await axios.put(`http://127.0.0.1:8000/tasks/${id}`, updates, 
        { headers: { Authorization: `Bearer ${idToken}` } }
      );
    } catch (error) {
      console.error('Update task failed:', error);
    }
  };

  const deleteTask = async (id: string) => {
    if (!idToken) throw new Error('Not authenticated');
    try {
      await axios.delete(`http://127.0.0.1:8000/tasks/${id}`, 
        { headers: { Authorization: `Bearer ${idToken}` } }
      );
    } catch (error) {
      console.error('Delete task failed:', error);
    }
  };

  const value = {
    state,
    dispatch,
    sendMessage,
    createTask,
    updateTask,
    deleteTask,
  };

  if (loading) return <div>Loading...</div>;  // Or spinner

  return <NovaContext.Provider value={value}>{children}</NovaContext.Provider>;
};

export const useNova = () => {
  const context = useContext(NovaContext);
  if (!context) throw new Error('useNova must be used within NovaProvider');
  return context;
};