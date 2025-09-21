import React, { useState } from 'react';
import { motion } from 'framer-motion';
import { 
  MessageSquare, 
  Plus, 
  Search, 
  Calendar,
  BarChart3,
  Settings,
  ChevronLeft,
  ChevronRight,
  Trash2,
  MoreVertical
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { ScrollArea } from '@/components/ui/scroll-area';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { useNova } from '@/context/NovaContext';
import type { ChatSession } from '@/api/types';
import { chatService } from '@/api/chatService';
/**
 * Nova Sidebar - Chat history and navigation
 * 
 * Features:
 * - Recent chat sessions with AI summaries
 * - Search functionality
 * - New chat creation
 * - View switching (chat, scheduler, dashboard, settings)
 * - Collapsible design
 * - Session management (delete, rename)
 */

interface SidebarProps {
  className?: string;
}

export default function Sidebar({ className = '' }: SidebarProps) {
  const { state, dispatch } = useNova();
  const [searchQuery, setSearchQuery] = useState('');
  const [filteredSessions, setFilteredSessions] = useState(state.sessions);

  // Handle search
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    if (!query.trim()) {
      setFilteredSessions(state.sessions);
      return;
    }

    const filtered = state.sessions.filter(session =>
      session.title.toLowerCase().includes(query.toLowerCase()) ||
      session.summary?.toLowerCase().includes(query.toLowerCase()) ||
      session.messages.some(msg => 
        msg.content.toLowerCase().includes(query.toLowerCase())
      )
    );
    setFilteredSessions(filtered);
  };

  // Handle new chat
  const handleNewChat = () => {
    // TODO: IMPLEMENT IN PRELOAD - window.api.createNewChat()
    const newSession: ChatSession = {
      id: `session-${Date.now()}`,
      title: 'New Chat',
      messages: [],
      createdAt: Date.now(),
      updatedAt: Date.now(),
    };

    dispatch({ type: 'SET_SESSIONS', payload: [newSession, ...state.sessions] });
    dispatch({ type: 'SET_CURRENT_SESSION', payload: newSession });
  };

  // Handle session selection
const handleSessionSelect = async (session: ChatSession) => {
  const history = await chatService.getChatHistory(session.id);
  dispatch({ type: 'SET_CURRENT_SESSION', payload: { ...session, messages: history } });
};

  // Handle session deletion
  const handleDeleteSession = (sessionId: string) => {
    // TODO: IMPLEMENT IN PRELOAD - window.api.deleteChatSession(sessionId)
    const updatedSessions = state.sessions.filter(s => s.id !== sessionId);
    dispatch({ type: 'SET_SESSIONS', payload: updatedSessions });
    
    if (state.currentSession?.id === sessionId) {
      dispatch({ type: 'SET_CURRENT_SESSION', payload: updatedSessions[0] || null });
    }
  };

  // Handle view switching
  const handleViewChange = (view: typeof state.view) => {
    dispatch({ type: 'SET_VIEW', payload: view });
  };

  // Toggle sidebar collapse
  const toggleCollapsed = () => {
    dispatch({ type: 'SET_SIDEBAR_COLLAPSED', payload: !state.sidebarCollapsed });
  };

  return (
    <motion.div 
      className={`sidebar-nova h-full flex flex-col ${className}`}
      animate={{ width: state.sidebarCollapsed ? 60 : 300 }}
      transition={{ type: 'spring', stiffness: 300, damping: 30 }}
    >
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          {!state.sidebarCollapsed && (
            <div className="flex items-center gap-2">
              <div className="w-8 h-8 bg-gradient-to-br from-primary to-accent rounded-lg flex items-center justify-center text-primary-foreground font-bold text-sm">
                N
              </div>
              <span className="font-semibold text-lg">Nova</span>
            </div>
          )}
          
          <Button
            size="sm"
            variant="ghost"
            onClick={toggleCollapsed}
            className="w-8 h-8 p-0 rounded-lg"
            aria-label={state.sidebarCollapsed ? 'Expand sidebar' : 'Collapse sidebar'}
          >
            {state.sidebarCollapsed ? <ChevronRight size={16} /> : <ChevronLeft size={16} />}
          </Button>
        </div>

        {/* Navigation Buttons */}
        {!state.sidebarCollapsed && (
          <div className="flex gap-1 mt-4">
            <Button
              size="sm"
              variant={state.view === 'chat' ? 'default' : 'ghost'}
              className="flex-1 btn-nova-ghost"
              onClick={() => handleViewChange('chat')}
            >
              <MessageSquare size={14} className="mr-1" />
              Chat
            </Button>
            
            <Button
              size="sm"
              variant="ghost"
              className="p-2"
              onClick={() => handleViewChange('scheduler')}
              aria-label="Scheduler"
            >
              <Calendar size={14} />
            </Button>
            
            <Button
              size="sm"
              variant="ghost"
              className="p-2"
              onClick={() => handleViewChange('dashboard')}
              aria-label="Dashboard"
            >
              <BarChart3 size={14} />
            </Button>
            
            <Button
              size="sm"
              variant="ghost"
              className="p-2"
              onClick={() => handleViewChange('settings')}
              aria-label="Settings"
            >
              <Settings size={14} />
            </Button>
          </div>
        )}
      </div>

      {/* New Chat & Search */}
      {!state.sidebarCollapsed && (
        <div className="p-4 space-y-3 border-b border-border">
          <Button
            onClick={handleNewChat}
            className="w-full btn-nova gap-2"
            size="sm"
          >
            <Plus size={16} />
            New Chat
          </Button>

          <div className="relative">
            <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground" size={14} />
            <Input
              placeholder="Search chats..."
              value={searchQuery}
              onChange={(e) => handleSearch(e.target.value)}
              className="pl-9 input-nova h-9"
            />
          </div>
        </div>
      )}

      {/* Chat Sessions List */}
      <ScrollArea className="flex-1">
        <div className="p-2">
          {state.sidebarCollapsed ? (
            // Collapsed view - show only icons
            <div className="space-y-2">
              {state.sessions.slice(0, 8).map((session) => (
                <Button
                  key={session.id}
                  size="sm"
                  variant={state.currentSession?.id === session.id ? 'default' : 'ghost'}
                  className="w-full h-10 p-0 rounded-lg justify-center"
                  onClick={() => handleSessionSelect(session)}
                  title={session.title}
                >
                  <MessageSquare size={16} />
                </Button>
              ))}
            </div>
          ) : (
            // Expanded view - show full session info
            <div className="space-y-1">
              {(searchQuery ? filteredSessions : state.sessions).map((session) => (
                <motion.div
                  key={session.id}
                  initial={{ opacity: 0, x: -20 }}
                  animate={{ opacity: 1, x: 0 }}
                  className={`group relative rounded-lg p-3 cursor-pointer transition-colors hover:bg-white/5 ${
                    state.currentSession?.id === session.id 
                      ? 'bg-primary/10 border border-primary/20' 
                      : 'border border-transparent'
                  }`}
                  onClick={() => handleSessionSelect(session)}
                >
                  <div className="flex items-start justify-between">
                    <div className="flex-1 min-w-0">
                      <div className="font-medium text-sm truncate">
                        {session.title}
                      </div>
                      
                      {session.summary && (
                        <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
                          {session.summary}
                        </div>
                      )}
                      
                      <div className="flex items-center gap-2 mt-2 text-xs text-muted-foreground">
                        <span>{session.messages.length} messages</span>
                        <span>•</span>
                        <span>{new Date(session.updatedAt).toLocaleDateString()}</span>
                      </div>
                    </div>

                    {/* Session Menu */}
                    <div className="opacity-0 group-hover:opacity-100 transition-opacity">
                      <DropdownMenu>
                        <DropdownMenuTrigger asChild>
                          <Button
                            size="sm"
                            variant="ghost"
                            className="w-6 h-6 p-0"
                            onClick={(e) => e.stopPropagation()}
                          >
                            <MoreVertical size={12} />
                          </Button>
                        </DropdownMenuTrigger>
                        <DropdownMenuContent align="end">
                          <DropdownMenuItem
                            className="text-destructive"
                            onClick={(e) => {
                              e.stopPropagation();
                              handleDeleteSession(session.id);
                            }}
                          >
                            <Trash2 className="mr-2 h-4 w-4" />
                            Delete Chat
                          </DropdownMenuItem>
                        </DropdownMenuContent>
                      </DropdownMenu>
                    </div>
                  </div>
                </motion.div>
              ))}

              {/* Empty State */}
              {filteredSessions.length === 0 && searchQuery && (
                <div className="text-center py-8 text-muted-foreground">
                  <Search size={32} className="mx-auto mb-2 opacity-50" />
                  <div className="text-sm">No chats found</div>
                  <div className="text-xs">Try a different search term</div>
                </div>
              )}
            </div>
          )}
        </div>
      </ScrollArea>

      {/* Privacy Indicator */}
      {!state.sidebarCollapsed && (
        <div className="p-4 border-t border-border">
          <div className="flex items-center gap-2 text-xs text-muted-foreground">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            <span>Local processing active</span>
          </div>
        </div>
      )}
    </motion.div>
  );
}