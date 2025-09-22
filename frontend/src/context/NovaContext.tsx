import React, { createContext, useContext, useReducer, useEffect } from 'react';
import type { 
  ChatSession, 
  ChatMessage, 
  SchedulerTask, 
  AgentOp,
  NovaRole,
  Integration 
} from '@/api/types';
import { chatService } from '@/api/chatService';
import { apiClient } from '@/api/client';

/**
 * Nova AI Assistant - Global State Management
 * 
 * Provides centralized state management for the Nova UI with mock data
 * for development and easy integration with Electron backend.
 */

type NovaState = {
  // Chat state
  currentSession: ChatSession | null;
  sessions: ChatSession[];
  isTyping: boolean;
  isProcessing: boolean;
  
  // Scheduler state  
  tasks: SchedulerTask[];
  
  // Agent operations
  operations: AgentOp[];
  
  // UI state
  view: 'chat' | 'scheduler' | 'dashboard' | 'settings';
  isMiniMode: boolean;
  sidebarCollapsed: boolean;
  
  // User preferences
  role: NovaRole;
  voiceEnabled: boolean;
  selectedModel: string;
  
  // Integrations
  integrations: Integration[];
};

type NovaAction = 
  | { type: 'SET_VIEW'; payload: NovaState['view'] }
  | { type: 'SET_MINI_MODE'; payload: boolean }
  | { type: 'SET_SIDEBAR_COLLAPSED'; payload: boolean }
  | { type: 'ADD_MESSAGE'; payload: { sessionId: string; message: ChatMessage } }
  | { type: 'SET_SESSIONS'; payload: ChatSession[] }
  | { type: 'SET_CURRENT_SESSION'; payload: ChatSession | null }
  | { type: 'SET_TYPING'; payload: boolean }
  | { type: 'ADD_TASK'; payload: SchedulerTask }
  | { type: 'UPDATE_TASK'; payload: { id: string; updates: Partial<SchedulerTask> } }
  | { type: 'DELETE_TASK'; payload: string }
  | { type: 'SET_TASKS'; payload: SchedulerTask[] }
  | { type: 'SET_OPERATIONS'; payload: AgentOp[] }
  | { type: 'SET_ROLE'; payload: NovaRole }
  | { type: 'SET_VOICE_ENABLED'; payload: boolean }
  | { type: 'SET_INTEGRATIONS'; payload: Integration[] }
  | { type: 'SET_PROCESSING'; payload: boolean };;



const mockTasks: SchedulerTask[] = [
  {
    id: 'task-1',
    title: 'Prepare Q4 presentation',
    description: 'Create slides for quarterly review meeting with stakeholders',
    deadline: '2024-10-15T14:00:00Z',
    priority: 'High',
    status: 'todo',
    tags: ['presentation', 'quarterly'],
    isAgenticTask: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-2', 
    title: 'Code review for API updates',
    description: 'Review pull requests for authentication service improvements',
    deadline: '2024-10-12T17:00:00Z',
    priority: 'Medium',
    status: 'inprogress', 
    tags: ['development', 'api'],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-3',
    title: 'Team standup notes',
    description: 'Document key decisions and action items from daily standups',
    deadline: '2024-10-11T09:30:00Z', 
    priority: 'Low',
    status: 'done',
    tags: ['documentation'],
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
];

const mockIntegrations: Integration[] = [
  { id: 'email', name: 'Email', enabled: true, status: 'connected', lastSync: Date.now() - 300000 },
  { id: 'calendar', name: 'Calendar', enabled: false, status: 'disconnected' },
  { id: 'smartwatch', name: 'Smartwatch', enabled: false, status: 'disconnected' },
  { id: 'device', name: 'Device Activity', enabled: true, status: 'connected', lastSync: Date.now() - 600000 },
];

const initialState: NovaState = {
  currentSession:[0] as unknown as ChatSession,
  sessions: [],
  isTyping: false,
  tasks: [],
  operations: [],
  view: 'chat',
  isMiniMode: false,
  sidebarCollapsed: false,
  role: 'friend',
  voiceEnabled: true,
  selectedModel: 'whisper-base',
  integrations: mockIntegrations,
  isProcessing: false,
};

function novaReducer(state: NovaState, action: NovaAction): NovaState {
  // Move const outside switch
  let updatedSessions = state.sessions;
  let updatedCurrentSession = state.currentSession;

  switch (action.type) {
    case 'SET_VIEW':
      return { ...state, view: action.payload };
    
    case 'SET_MINI_MODE':
      return { ...state, isMiniMode: action.payload };
    
    case 'SET_SIDEBAR_COLLAPSED':
      return { ...state, sidebarCollapsed: action.payload };
      
    case 'ADD_MESSAGE':
      const { sessionId, message } = action.payload;
      updatedSessions = state.sessions.map(session => 
        session.id === sessionId 
          ? { ...session, messages: [...session.messages, message], updatedAt: Date.now() }
          : session
      );
      updatedCurrentSession = state.currentSession?.id === sessionId
        ? { ...state.currentSession, messages: [...state.currentSession.messages, message] }
        : state.currentSession;
      return {
        ...state,
        sessions: updatedSessions,
        currentSession: updatedCurrentSession
      };
    
    case 'SET_SESSIONS':
      return { ...state, sessions: action.payload };
      
    case 'SET_CURRENT_SESSION':
      return { ...state, currentSession: action.payload };
      
    case 'SET_TYPING':
      return { ...state, isTyping: action.payload };
      
    case 'ADD_TASK':
      return { ...state, tasks: [...state.tasks, action.payload] };
      
    case 'UPDATE_TASK':
      return {
        ...state,
        tasks: state.tasks.map(task => 
          task.id === action.payload.id 
            ? { ...task, ...action.payload.updates, updatedAt: new Date().toISOString() }
            : task
        )
      };
      
    case 'DELETE_TASK':
      return { ...state, tasks: state.tasks.filter(task => task.id !== action.payload) };
      
    case 'SET_TASKS':
      return { ...state, tasks: action.payload };
      
    case 'SET_OPERATIONS':
      return { ...state, operations: action.payload };
      
    case 'SET_ROLE':
      return { ...state, role: action.payload };
      
    case 'SET_VOICE_ENABLED':
      return { ...state, voiceEnabled: action.payload };
      
    case 'SET_INTEGRATIONS':
      return { ...state, integrations: action.payload };

    case 'SET_PROCESSING':  // NEW
      return { ...state, isProcessing: action.payload };  
      
    default:
      return state;
  }
}

const NovaContext = createContext<{
  state: NovaState;
  dispatch: React.Dispatch<NovaAction>;
} | null>(null);

export function NovaProvider({ children }: { children: React.ReactNode }) {
  const [state, dispatch] = useReducer(novaReducer, initialState);

  // Set up chat service callbacks
  useEffect(() => {
    chatService.setCallbacks({
      onMessage: (message) => {
        if (state.currentSession) {
          dispatch({
            type: 'ADD_MESSAGE',
            payload: { sessionId: state.currentSession.id, message }
          });
        }
      },
      onTyping: (isTyping) => {
        dispatch({ type: 'SET_TYPING', payload: isTyping });
      },
      onError: (error) => {
        console.error('Chat service error:', error);
      },
      onSessionUpdate: (session) => {
        dispatch({ type: 'SET_CURRENT_SESSION', payload: session });
      }
    });
  }, [state.currentSession]);

  // Load initial data from API
  useEffect(() => {
    const loadInitialData = async () => {
    try {
      // Load chat sessions
      const sessions = await chatService.getChatSessions();
      dispatch({ type: 'SET_SESSIONS', payload: sessions });
      
      let currentSession = sessions[0] || chatService.createNewSession();
      if (!currentSession) {
        const history = await chatService.getChatHistory(currentSession.id);
        currentSession = { ...currentSession, messages: history };}
      dispatch({ type: 'SET_CURRENT_SESSION', payload: currentSession });
      
      // Load messages for current session
      if (currentSession) {
        const history = await chatService.getChatHistory(currentSession.id);
        // Update current session with messages (if not already loaded)
        dispatch({
          type: 'SET_CURRENT_SESSION',
          payload: { ...currentSession, messages: history }
        });
      }

      // Load tasks
      const tasks = await apiClient.getTasks();
      dispatch({ type: 'SET_TASKS', payload: tasks });

      // Load operations
      const operations = await apiClient.getOperations();
      dispatch({ type: 'SET_OPERATIONS', payload: operations });
    } catch (error) {
      console.error('Failed to load initial data:', error);
    // Set defaults to avoid undefined
    dispatch({ type: 'SET_SESSIONS', payload: [] });
    dispatch({ type: 'SET_TASKS', payload: [] });
    dispatch({ type: 'SET_OPERATIONS', payload: [] });
    // Create a default session
    const defaultSession = { id: 'default', title: 'New Chat', messages: [], createdAt: Date.now(), updatedAt: Date.now() };
    dispatch({ type: 'SET_CURRENT_SESSION', payload: defaultSession });
    }
  };
  loadInitialData();
}, []);



  // Simulate some dynamic updates for demo (reduced frequency)
  useEffect(() => {
    const interval = setInterval(() => {
      // Randomly update agent operations for demo
      if (Math.random() > 0.9) {
        const mockOps: AgentOp[] = [
          {
            id: `op-${Date.now()}`,
            title: 'Processing email batch',
            desc: 'Categorizing and prioritizing incoming messages',
            status: 'running',
            progress: Math.floor(Math.random() * 100),
            startTime: Date.now() - Math.random() * 60000,
          }
        ];
        dispatch({ type: 'SET_OPERATIONS', payload: mockOps });
      }
    }, 30000); // Reduced frequency

    return () => clearInterval(interval);
  }, []);

  return (
    <NovaContext.Provider value={{ state, dispatch }}>
      {children}
    </NovaContext.Provider>
  );
}

export function useNova() {
  const context = useContext(NovaContext);
  if (!context) {
    throw new Error('useNova must be used within a NovaProvider');
  }
  return context;
}