import { contextBridge, ipcRenderer } from 'electron';
console.log('PRELOAD: Starting preload script...');

contextBridge.exposeInMainWorld('api', {
  // Window expansion/minimization with proper error handling
  requestExpand: async () => {
    console.log('RENDERER: Calling requestExpand via IPC...');
    try {
      const result = await ipcRenderer.invoke('requestExpand');
      console.log('RENDERER: requestExpand succeeded:', result);
      return result;
    } catch (error) {
      console.error('RENDERER: requestExpand failed:', error);
      throw error;
    }
  },
  requestMinimize: async () => {
    console.log('RENDERER: Calling requestMinimize...');
    try {
      const result = await ipcRenderer.invoke('requestMinimize');
      console.log('RENDERER: requestMinimize succeeded:', result);
      return result;
    } catch (error) {
      console.error('RENDERER: requestMinimize failed:', error);
      throw error;
    }
  },
  setAlwaysOnTop: (flag) => ipcRenderer.invoke('setAlwaysOnTop', flag),
  // Window controls with proper error handling
  windowMinimize: () => {
    try {
      ipcRenderer.send("window:minimize");
    } catch (error) {
      console.error('RENDERER: windowMinimize failed:', error);
    }
  },
  windowMaximize: () => {
    try {
      ipcRenderer.send("window:maximize");
    } catch (error) {
      console.error('RENDERER: windowMaximize failed:', error);
    }
  },
  setAuthStatus: (status) => ipcRenderer.send('auth-status', status),
  windowClose: () => {
    try {
      ipcRenderer.send("window:close");
    } catch (error) {
      console.error('RENDERER: windowClose failed:', error);
    }
  },
  // NEW: Mini window specific close
  miniClose: () => {
    try {
      ipcRenderer.send("mini:close");
    } catch (error) {
      console.error('RENDERER: miniClose failed:', error);
    }
  },
  // Voice transcription
  transcribeStart: (sessionId) => ipcRenderer.invoke('transcribeStart', sessionId),
  transcribeStop: (sessionId) => ipcRenderer.invoke('transcribeStop', sessionId),
  transcribeStream: (sessionId, cb) => {
    ipcRenderer.on(`transcribe-stream-${sessionId}`, (event, text, partial) => cb(text, partial));
    return () => ipcRenderer.removeAllListeners(`transcribe-stream-${sessionId}`);
  },
  // Local models
  listLocalModels: () => ipcRenderer.invoke('listLocalModels'),
  // Text-to-speech
  speak: (text, voiceId) => ipcRenderer.invoke('speak', text, voiceId),
  // Chat functionality - Updated: Real API with token
  sendMessage: async (message, sessionId, idToken) => {
    if (!idToken) throw new Error('No auth token');
    const response = await fetch('http://localhost:8000/process_query', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        'Authorization': `Bearer ${idToken}`,
      },
      body: JSON.stringify({ query: message, session_id: sessionId }),
    });
    if (!response.ok) throw new Error(await response.text());
    const data = await response.json();
    return data.result;
  },
  onMessageStream: (cb) => {
    ipcRenderer.on('message-stream', (event, message) => cb(message));
    return () => ipcRenderer.removeAllListeners('message-stream');
  },
  // Agent operations
  executeAction: (action) => ipcRenderer.invoke('executeAction', action),
  onAgentOpsUpdate: (cb) => {
    ipcRenderer.on('agent-ops-update', (event, ops) => cb(ops));
    return () => ipcRenderer.removeAllListeners('agent-ops-update');
  },
  // Task management - New: Real API
  createTask: async (task, idToken) => {
    const response = await fetch('http://localhost:8000/tasks', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
      body: JSON.stringify(task),
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  updateTask: async (id, updates, idToken) => {
    const response = await fetch(`http://localhost:8000/tasks/${id}`, {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
      body: JSON.stringify(updates),
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  deleteTask: async (id, idToken) => {
    const response = await fetch(`http://localhost:8000/tasks/${id}`, {
      method: 'DELETE',
      headers: { 'Authorization': `Bearer ${idToken}` },
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  getTasks: async (idToken) => {
    const response = await fetch('http://localhost:8000/tasks', {
      headers: { 'Authorization': `Bearer ${idToken}` },
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  // Chat sessions - TODO: Implement API
  getChatSessions: () => ipcRenderer.invoke('getChatSessions'),
  getChatSession: (id) => ipcRenderer.invoke('getChatSession', id),
  deleteChatSession: (id) => ipcRenderer.invoke('deleteChatSession', id),
  searchChats: (query) => ipcRenderer.invoke('searchChats', query),
  // Integrations
  openExternalAuth: (service) => ipcRenderer.invoke('openExternalAuth', service),
  enableIntegration: (service, credentials) => ipcRenderer.invoke('enableIntegration', service, credentials),
  getIntegrations: () => ipcRenderer.invoke('getIntegrations'),
  // Export functionality
  exportDashboardPDF: (payload) => ipcRenderer.invoke('exportDashboardPDF', payload),
  // User preferences - New: Real API
  getUserPreferences: async (idToken) => {
    const response = await fetch('http://localhost:8000/profile', {
      headers: { 'Authorization': `Bearer ${idToken}` },
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  updateUserPreferences: async (prefs, idToken) => {
    const response = await fetch('http://localhost:8000/profile', {
      method: 'PUT',
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${idToken}` },
      body: JSON.stringify(prefs),
    });
    if (!response.ok) throw new Error(await response.text());
    return await response.json();
  },
  // Notifications
  notify: (title, body) => ipcRenderer.invoke('notify', title, body),
  // Theme changes
  onThemeChange: (cb) => {
    ipcRenderer.on('theme-change', (event, theme) => cb(theme));
    return () => ipcRenderer.removeAllListeners('theme-change');
  },
  // App version
  getAppVersion: () => ipcRenderer.invoke('getAppVersion'),
  // Window state detection
  isElectron: true,
  isMiniMode: typeof window !== 'undefined' && window.isMiniMode,
  // New: Auth status for Electron
  setAuthStatus: (status) => ipcRenderer.send('auth-status', status),
});

console.log('PRELOAD: contextBridge exposed window.api successfully');