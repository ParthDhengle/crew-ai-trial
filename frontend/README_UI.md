# Nova AI Assistant - UI Implementation Guide

This React TypeScript UI provides a complete Nova AI assistant interface ready for Electron integration.

## Architecture Overview

- **MiniWidget**: Compact floating widget (80-110px) for always-on-top mode
- **FullChat**: Main chat interface with sidebar and agent operations panel  
- **Scheduler**: Kanban-style task management with drag & drop
- **Dashboard**: Compact, exportable overview card
- **Settings**: Integration management and voice configuration

## Required Electron API Implementation

The UI expects these `window.api` methods to be implemented in your Electron preload/main processes:

### Window Control
```typescript
window.api.requestExpand(): void
window.api.requestMinimize(): void  
window.api.setAlwaysOnTop(flag: boolean): void
```

### Voice (Local Whisper)
```typescript
window.api.transcribeStart(sessionId: string): Promise<void>
window.api.transcribeStop(sessionId: string): Promise<void>
window.api.transcribeStream(sessionId: string, callback): void
window.api.listLocalModels(): Promise<string[]>
window.api.speak(text: string, voiceId?: string): Promise<void>
```

### Chat & AI
```typescript
window.api.sendMessage(message: string, sessionId?: string): Promise<{sessionId: string}>
window.api.onMessageStream(callback): Unsubscribe
```

### Agent Operations
```typescript
window.api.executeAction(action: {type: string, payload?: any}): Promise<{ok: boolean}>
window.api.onAgentOpsUpdate(callback): Unsubscribe
```

### Data Management
```typescript
window.api.createTask(task): Promise<SchedulerTask>
window.api.updateTask(id: string, updates): Promise<SchedulerTask>  
window.api.deleteTask(id: string): Promise<void>
window.api.getChatSessions(): Promise<ChatSession[]>
```

### Integrations
```typescript
window.api.openExternalAuth(service: string): Promise<void>
window.api.enableIntegration(service: string, credentials): Promise<{ok: boolean}>
```

### Exports  
```typescript
window.api.exportDashboardPDF(payload: {html: string}): Promise<{path: string}>
```

## Integration Checklist

1. **Implement Electron preload API** - All `window.api` methods above
2. **Set up local Whisper service** - For voice transcription
3. **Configure window management** - Always-on-top, minimize/expand behavior  
4. **Add click-outside detection** - To minimize widget when focus lost
5. **Implement TTS service** - For read-aloud functionality
6. **Set up file system access** - For PDF exports and attachments
7. **Configure OAuth flows** - For email/calendar integrations
8. **Add keyboard shortcuts** - Global hotkeys for toggle and search

## Running the UI

```bash
npm install
npm run dev
```

The UI includes mock data and will run standalone for development. All Electron-specific features are gracefully mocked with console logs.