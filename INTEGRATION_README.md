# Nova AI Assistant - Frontend-Backend Integration

This document explains how the frontend Electron desktop application is connected to the backend FastAPI server, including authentication and chat functionality.

## 🏗️ Architecture Overview

### Backend (FastAPI)

- **Location**: `src/app.py`
- **Port**: 8000
- **Authentication**: Firebase-based with JWT tokens
- **Key Features**:
  - User authentication (login/signup)
  - Chat processing with AI agent
  - Task management
  - Profile management
  - Operations queue

### Frontend (React + Electron)

- **Location**: `frontend/`
- **Port**: 5173 (development)
- **Authentication**: Handled by frontend with token storage
- **Key Features**:
  - Login/signup forms
  - Real-time chat interface
  - Mini widget and full chat views
  - Shared state management

## 🔐 Authentication Flow

1. **User Registration/Login**: Frontend sends credentials to `/auth/signup` or `/auth/login`
2. **Token Storage**: Backend returns JWT token, frontend stores it in localStorage
3. **API Requests**: All subsequent requests include `Authorization: Bearer <token>` header
4. **Token Validation**: Backend validates tokens on protected routes
5. **Logout**: Frontend clears stored tokens

## 💬 Chat Integration

### Shared State Management

- Both `FullChat` and `MiniWidget` components use the same `NovaContext`
- Messages are synchronized through the `chatService`
- Real-time updates via callback system

### Message Flow

1. User types message in either component
2. Message sent via `chatService.sendMessage()`
3. Backend processes with AI agent
4. Response returned and added to shared state
5. Both components automatically update

## 🚀 Quick Start

### Option 1: Automated Startup

```bash
# Run the startup script (starts both backend and frontend)
python start_nova.py
```

### Option 2: Manual Startup

#### Backend

```bash
cd src
python app.py
```

#### Frontend

```bash
cd frontend
npm run dev
```

### Option 3: Test Integration

```bash
# Test if backend is working
python test_integration.py
```

## 📁 Key Files

### Backend

- `src/app.py` - Main FastAPI application
- `src/firebase_client.py` - Firebase authentication
- `src/crew.py` - AI agent implementation

### Frontend

- `frontend/src/api/client.ts` - API client with authentication
- `frontend/src/api/chatService.ts` - Chat service layer
- `frontend/src/context/AuthContext.tsx` - Authentication context
- `frontend/src/context/NovaContext.tsx` - Global state management
- `frontend/src/components/LoginForm.tsx` - Authentication UI
- `frontend/src/components/FullChat.tsx` - Full chat interface
- `frontend/src/components/MiniWidget.tsx` - Mini chat widget

## 🔧 Configuration

### Backend Configuration

- Firebase credentials: `NOVA_firebase_credentials.json`
- CORS enabled for frontend domains
- JWT token validation

### Frontend Configuration

- API base URL: `http://127.0.0.1:8000`
- Token storage in localStorage
- Error handling and retry logic

## 🧪 Testing

### Backend API Testing

```bash
# Test authentication
curl -X POST "http://127.0.0.1:8000/auth/signup" \
  -H "Content-Type: application/json" \
  -d '{"email": "test@example.com", "password": "testpass123"}'

# Test chat (with token)
curl -X POST "http://127.0.0.1:8000/process_query" \
  -H "Authorization: Bearer YOUR_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"query": "Hello Nova", "session_id": "test-session"}'
```

### Frontend Testing

1. Open http://localhost:5173
2. Create account or login
3. Send messages in chat
4. Test mini widget functionality

## 🐛 Troubleshooting

### Common Issues

1. **Backend not starting**

   - Check if port 8000 is available
   - Verify Python dependencies are installed
   - Check Firebase credentials

2. **Frontend not connecting**

   - Verify backend is running on port 8000
   - Check CORS settings
   - Check browser console for errors

3. **Authentication issues**

   - Clear localStorage and try again
   - Check Firebase configuration
   - Verify token format

4. **Chat not working**
   - Check if AI agent is properly configured
   - Verify session ID handling
   - Check backend logs

### Debug Mode

- Backend logs: Check console output
- Frontend logs: Open browser DevTools
- Network requests: Check Network tab in DevTools

## 🔄 Development Workflow

1. **Backend Changes**: Restart `python app.py`
2. **Frontend Changes**: Hot reload (automatic)
3. **Database Changes**: May require backend restart
4. **Authentication Changes**: Clear localStorage

## 📊 Monitoring

- **Backend Health**: http://127.0.0.1:8000/docs
- **Frontend DevTools**: F12 in browser
- **Logs**: Check console output for both services

## 🚀 Production Deployment

### Backend

- Use production WSGI server (Gunicorn)
- Configure proper CORS origins
- Set up SSL certificates
- Use environment variables for secrets

### Frontend

- Build for production: `npm run build`
- Configure Electron packaging
- Set up auto-updater
- Configure production API endpoints

## 📝 Notes

- Both chat components share the same state and session
- Authentication is handled entirely by the frontend
- All API communication goes through the centralized `apiClient`
- Error handling includes user-friendly messages
- The system is designed to work offline (with cached data)

## 🤝 Contributing

When making changes:

1. Test both backend and frontend
2. Verify authentication flow
3. Check chat synchronization
4. Update this documentation if needed
