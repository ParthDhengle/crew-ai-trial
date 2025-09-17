import React, { createContext, useContext, useReducer, useEffect } from 'react';
import type { 
  ChatSession, 
  ChatMessage, 
  SchedulerTask, 
  AgentOp,
  NovaRole,
  Integration 
} from '@/api/types';

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
  | { type: 'SET_OPERATIONS'; payload: AgentOp[] }
  | { type: 'SET_ROLE'; payload: NovaRole }
  | { type: 'SET_VOICE_ENABLED'; payload: boolean }
  | { type: 'SET_INTEGRATIONS'; payload: Integration[] };

// Mock data for development
const mockSessions: ChatSession[] = [
  {
    id: 'session-1',
    title: 'Project Planning Discussion',
    summary: 'Discussed Q4 project timeline and resource allocation',
    createdAt: Date.now() - 86400000,
    updatedAt: Date.now() - 3600000,
    messages: [
      {
        id: 'msg-1',
        content: "Hey Nova, I need help planning my Q4 projects. Can you help me organize my tasks?",
        role: 'user',
        timestamp: Date.now() - 86400000,
      },
      {
        id: 'msg-2', 
        content: "Of course! I'd be happy to help you plan your Q4 projects. Let me analyze your current workload and suggest an optimal timeline. I can also create a structured task breakdown for you.",
        role: 'assistant',
        timestamp: Date.now() - 86390000,
        actions: [
          { type: 'accept_schedule', label: 'Create Schedule', payload: {} },
          { type: 'run_operation', label: 'Analyze Workload', payload: { operation: 'workload_analysis' } }
        ]
      },
      {
        id: 'msg-3',
        content: "That sounds perfect. I have about 15 hours per week available for project work.",
        role: 'user', 
        timestamp: Date.now() - 86300000,
      },
    ]
  },
  {
    id: 'session-2',
    title: 'Email Management',
    summary: 'Set up automated email responses and sorting rules',
    createdAt: Date.now() - 172800000,
    updatedAt: Date.now() - 7200000,
    messages: [
      {
        id: 'msg-4',
        content: "Can you help me set up some email automation rules?",
        role: 'user',
        timestamp: Date.now() - 172800000,
      },
      {
        id: 'msg-5',
        content: "Absolutely! I can help you create email filters, automated responses, and priority sorting. What type of emails would you like to automate first?",
        role: 'assistant', 
        timestamp: Date.now() - 172750000,
      }
    ]
  }
];

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
  currentSession: mockSessions[0],
  sessions: mockSessions,
  isTyping: false,
  tasks: mockTasks,
  operations: [],
  view: 'chat',
  isMiniMode: false,
  sidebarCollapsed: false,
  role: 'friend',
  voiceEnabled: true,
  selectedModel: 'whisper-base',
  integrations: mockIntegrations,
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
      
    case 'SET_OPERATIONS':
      return { ...state, operations: action.payload };
      
    case 'SET_ROLE':
      return { ...state, role: action.payload };
      
    case 'SET_VOICE_ENABLED':
      return { ...state, voiceEnabled: action.payload };
      
    case 'SET_INTEGRATIONS':
      return { ...state, integrations: action.payload };
      
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

  // Simulate some dynamic updates for demo
  useEffect(() => {
    const interval = setInterval(() => {
      // Randomly update agent operations for demo
      if (Math.random() > 0.8) {
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
    }, 10000);

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