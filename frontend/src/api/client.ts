// frontend/src/api/client.ts (fixed - updated sendMessage type and added getChatSession)
import type {
  ChatMessage,
  ChatSession,
  SchedulerTask,
  AgentOp,
  NovaRole
} from './types';
// API Configuration
const API_BASE_URL = 'http://127.0.0.1:8001';
import { getAuth } from 'firebase/auth';
import { useAuth } from '@/context/AuthContext';
// Auth token management
class AuthManager {
  private token: string | null = null;
  private uid: string | null = null;

  setToken(token: string) {
    this.token = token;
  }
  private getHeaders() {
    const { token } = this.getAuth();
    return token ? { Authorization: `Bearer ${token}` } : {};
  }
  setAuth(token: string, uid: string) {
    this.token = token;
    this.uid = uid;
    localStorage.setItem('nova_auth_token', token);
    localStorage.setItem('nova_uid', uid);
  }

  getAuth() {
    if (!this.token) {
      this.token = localStorage.getItem('nova_auth_token');
      this.uid = localStorage.getItem('nova_uid');
    }
    return { token: this.token, uid: this.uid };
  }

  clearAuth() {
    this.token = null;
    this.uid = null;
    localStorage.removeItem('nova_auth_token');
    localStorage.removeItem('nova_uid');
  }

  isAuthenticated() {
    const { token } = this.getAuth();
    return !!token;
  }
}

const authManager = new AuthManager();

// HTTP Client with error handling
class ApiClient {
  private baseURL: string;

  constructor(baseURL: string) {
    this.baseURL = baseURL;
  }
  private token: string | null = null;

  setToken(token: string) {
    this.token = token;
  }

  private getHeaders() {
    return this.token ? { Authorization: `Bearer ${this.token}` } : {};
  }
  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const authInstance = getAuth(); // NEW: Get auth instance
    let token: string | undefined;
    if (authInstance.currentUser) {
      token = await authInstance.currentUser.getIdToken(/* forceRefresh */ false); // Fetch fresh if needed
    }

    const config: RequestInit = {
      ...options,
      headers: {
        'Content-Type': 'application/json',
        ...(token && { 'Authorization': `Bearer ${token}` }),
        ...options.headers,
      },
    };

    try {
      const response = await fetch(`${this.baseURL}${endpoint}`, config);
     
      if (!response.ok) {
        if (response.status === 401) {
          authManager.clearAuth();
          // NEW: Also sign out from Firebase
          await authInstance.signOut();
          throw new Error('Authentication failed. Please login again.');
        }
       
        const errorData = await response.json().catch(() => ({}));
        throw new Error(errorData.detail || `HTTP ${response.status}: ${response.statusText}`);
      }

      return await response.json();
    } catch (error) {
      console.error('API Request failed:', error);
      throw error;
    }
  }

  // Auth endpoints
  async login(email: string, password: string) {
    const response = await this.request<{ 
      uid: string; 
      custom_token: string; 
      profile_complete: boolean; // ADD THIS LINE
    }>('/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
   
    authManager.setAuth(response.custom_token, response.uid);
    return response;
  }

  async signup(email: string, password: string) {
    const response = await this.request<{ 
      uid: string; 
      custom_token: string; 
      profile_complete: boolean; // ADD THIS LINE
    }>('/auth/signup', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    });
   
    authManager.setAuth(response.custom_token, response.uid);
    return response;
  }

  async logout() {
    authManager.clearAuth();
  }

  // Chat endpoints
  async sendMessage(query: string, sessionId?: string) {
    const response = await this.request<{ result: { display_response: string; mode: string }; session_id: string; }>('/process_query', {
      method: 'POST',
      body: JSON.stringify({ query, session_id: sessionId }),
    });
    return response;
  }

  async getChatHistory(sessionId?: string) {
    const params = sessionId ? `?session_id=${sessionId}` : '';
    return this.request<ChatMessage[]>(`/chat_history${params}`);
  }

  async getChatSessions() {
    return this.request<ChatSession[]>('/chat_sessions');
  }

  // Added getChatSession to fetch a single session with messages
  async getChatSession(sessionId: string): Promise<ChatSession> {
    const sessions = await this.getChatSessions();
    const session = sessions.find(s => s.id === sessionId);
    if (!session) {
      throw new Error('Session not found');
    }
    const history = await this.getChatHistory(sessionId);
    return { ...session, messages: history };
  }

  // Task endpoints
  async getTasks() {
    return this.request<SchedulerTask[]>('/api/tasks');
  }
  async completeProfile(profileData: any) {
    const response = await this.request<{ success: boolean; profile_complete: boolean }>('/profile/complete', {
      method: 'POST',
      body: JSON.stringify(profileData),
    });
    return response;
  }
  async createTask(task: Omit<SchedulerTask, 'id' | 'createdAt' | 'updatedAt'>) {
    const response = await this.request<{ task_id: string }>('/tasks', {
      method: 'POST',
      body: JSON.stringify({
        title: task.title,
        description: task.description,
        deadline: task.deadline,
        priority: task.priority,
        tags: task.tags || [],
      }),
    });
   
    return {
      ...task,
      id: response.task_id,
      createdAt: new Date().toISOString(),
      updatedAt: new Date().toISOString(),
    };
  }

  async updateTask(id: string, updates: Partial<SchedulerTask>) {
    await this.request(`/tasks/${id}`, {
      method: 'PUT',
      body: JSON.stringify({
        status: updates.status,
        title: updates.title,
        description: updates.description,
        deadline: updates.deadline,
        priority: updates.priority,
        tags: updates.tags,
      }),
    });
   
    return { ...updates, id, updatedAt: new Date().toISOString() };
  }

  async deleteTask(id: string) {
    await this.request(`/tasks/${id}`, {
      method: 'DELETE',
    });
  }

  // Profile endpoints
  async getProfile() {
    return this.request('/profile');
  }

  async updateProfile(updates: any) {
    await this.request('/profile', {
      method: 'PUT',
      body: JSON.stringify(updates),
    });
  }

  // Operations endpoints
  async getOperations(status?: string) {
    const params = status ? `?status=${status}` : '';
    return this.request<AgentOp[]>(`/operations${params}`);
  }
  async queueOperation(name: string, parameters: any) {
    const response = await this.request<{ op_id: string }>('/operations', {
      method: 'POST',
      body: JSON.stringify({ name, parameters }),
    });
    return response.op_id;
  }

  async deleteChatSession(sessionId: string) {
    await this.request(`/chat_sessions/${sessionId}`, { method: 'DELETE' });
  }
}

// Create API client instance
export const apiClient = new ApiClient(API_BASE_URL);

// Export auth manager for direct access
export { authManager };

// Helper function to check if user is authenticated
export const isAuthenticated = () => useAuth().isAuthenticated;

// Helper function to get current user info
export const getCurrentUser = () => {
  const { uid } = authManager.getAuth();
  return { uid };
};
export { API_BASE_URL };