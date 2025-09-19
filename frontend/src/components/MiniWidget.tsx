import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  Mic,
  MicOff,
  Maximize2,
  MoreVertical,
  Settings,
  X,
  MessageSquare,
  Send,
  User,
  Bot,
  PlusCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useWindowControls } from '@/hooks/useElectronApi';
import { useNova } from '@/context/NovaContext';
import { useAuth } from '@/hooks/useAuth';
import type { ChatMessage } from '@/api/types';

interface MiniWidgetProps {
  className?: string;
  unreadCount?: number;
}

export default function MiniWidget({
  className = '',
  unreadCount = 0
}: MiniWidgetProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [showMenu, setShowMenu] = useState(false);
  const [isExpanding, setIsExpanding] = useState(false);
  const [isTyping, setIsTyping] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);

  const { expand } = useWindowControls();
  const { state, dispatch } = useNova();
  const { idToken } = useAuth();

  // Last 3 messages for preview
  const previewMessages = state.currentSession?.messages.slice(-3) || [];

  // Handle expand
  const handleExpand = async () => {
    setIsExpanding(true);
    try {
      await expand();
      setTimeout(() => setIsExpanding(false), 600);
    } catch (error) {
      console.error('MINI: Expand failed:', error);
      setIsExpanding(false);
    }
  };

  // Handle close
  const handleClose = () => {
    if (window.api) {
      (window as any).api.miniClose?.();
    } else {
      window.close();
    }
  };

  // ✅ Create new chat session
  const handleNewChat = () => {
    const newSession = {
      id: `session-${Date.now()}`,
      title: "New Chat",
      messages: [] as ChatMessage[],
      createdAt: Date.now(),
      updatedAt: Date.now(), 
    };
    dispatch({ type: 'ADD_SESSION', payload: newSession });
    dispatch({ type: 'SET_CURRENT_SESSION', payload: newSession });
  };

  // ✅ Quick send to backend
  const handleQuickSend = async () => {
    const message = state.draftMessage.trim();
    if (!message) {
      await handleExpand();
      return;
    }
    if (!idToken || !state.currentSession) return;
    const userMessage: ChatMessage = {
      id: `msg-${Date.now()}`,
      content: message,
      role: 'user',
      timestamp: Date.now(),
    };
    dispatch({
      type: 'ADD_MESSAGE',
      payload: { sessionId: state.currentSession.id, message: userMessage }
    });
    dispatch({ type: 'SET_DRAFT', payload: '' });  // Clear draft
    setIsTyping(true);
    try {
      const aiContent = await window.api.sendMessage(
        userMessage.content,
        state.currentSession.id,
        idToken
      );
      const aiMessage: ChatMessage = {
        id: `msg-${Date.now()}-ai`,
        content: aiContent.trim(),
        role: 'assistant',
        timestamp: Date.now(),
      };
      dispatch({
        type: 'ADD_MESSAGE',
        payload: { sessionId: state.currentSession.id, message: aiMessage }
      });
    } catch (err) {
      console.error("QuickSend failed:", err);
    } finally {
      setIsTyping(false);
    }
  };

  // Scroll preview
  useEffect(() => {
    scrollRef.current?.scrollTo({
      top: scrollRef.current.scrollHeight,
      behavior: 'smooth'
    });
  }, [previewMessages]);

  return (
    <motion.div
      className={`glass-nova rounded-xl border border-primary/30 shadow-2xl w-full h-full ${className}`}
      initial={{ scale: 0.9, opacity: 0, y: 20 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Expanding overlay */}
      {isExpanding && (
        <motion.div
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="absolute inset-0 bg-background/80 backdrop-blur-sm z-50 flex items-center justify-center"
        >
          <div className="text-center">
            <div className="w-8 h-8 border-2 border-primary border-t-transparent rounded-full animate-spin mx-auto mb-2" />
            <p className="text-sm text-muted-foreground">Expanding...</p>
          </div>
        </motion.div>
      )}

      {/* Header */}
      <div
        className="titlebar flex items-center justify-between px-3 py-2 border-b border-border/50 text-sm"
        style={{ WebkitAppRegion: 'drag' } as React.CSSProperties}
      >
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          <span>{state.currentSession?.title || "Nova Chat"}</span>
          {unreadCount > 0 && (
            <Badge variant="secondary" className="text-xs px-1.5 py-0">
              {unreadCount}
            </Badge>
          )}
        </div>

        <div className="flex items-center gap-1" style={{ WebkitAppRegion: 'no-drag' } as React.CSSProperties}>
          {/* Expand */}
          <Button size="sm" variant="ghost" onClick={handleExpand} disabled={isExpanding || isTyping} className="w-6 h-6 p-0">
            <Maximize2 size={12} />
          </Button>
          {/* Close */}
          <Button size="sm" variant="ghost" onClick={handleClose} className="w-6 h-6 p-0 text-red-400">
            <X size={12} />
          </Button>
          {/* Menu */}
          <DropdownMenu open={showMenu} onOpenChange={setShowMenu}>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="w-6 h-6 p-0">
                <MoreVertical size={12} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleExpand}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Full Chat
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleNewChat}>
                <PlusCircle className="mr-2 h-4 w-4" />
                New Chat
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => dispatch({ type: 'SET_VIEW', payload: 'settings' })}>
                <Settings className="mr-2 h-4 w-4" />
                Settings
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleClose} className="text-red-400">
                <X className="mr-2 h-4 w-4" />
                Close Nova
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Messages preview */}
      <ScrollArea className="flex-1 px-3 py-2" ref={scrollRef}>
        <div className="space-y-2">
          {previewMessages.length === 0 ? (
            <motion.div className="text-center text-xs text-muted-foreground py-8">
              <Bot size={24} className="mx-auto mb-2 text-primary/50" />
              <p>Start a conversation!</p>
            </motion.div>
          ) : (
            <AnimatePresence>
              {previewMessages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div
                    className={`max-w-[200px] rounded-lg px-2 py-1 text-xs ${
                      msg.role === 'user'
                        ? 'bg-primary text-primary-foreground'
                        : 'bg-muted/50 text-muted-foreground border border-border/30'
                    }`}
                  >
                    <div className="flex items-center gap-1 mb-1">
                      {msg.role === 'user' ? <User size={8} /> : <Bot size={8} className="text-primary" />}
                      <span className="font-medium">{msg.role === 'user' ? 'You' : 'Nova'}</span>
                    </div>
                    <div className="whitespace-pre-wrap">{msg.content}</div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}
          {isTyping && (
            <motion.div className="flex justify-start">
              <div className="bg-muted/50 rounded-lg px-2 py-1 border border-border/30 text-xs">
                Nova is typing...
              </div>
            </motion.div>
          )}
        </div>
      </ScrollArea>

      {/* Input */}
      <div className="border-t border-border/50 p-2 flex gap-1">
        <Input
          value={state.draftMessage}
          onChange={(e) => dispatch({ type: 'SET_DRAFT', payload: e.target.value })}
          placeholder="Quick message..."
          className="text-xs h-8 flex-1"
          disabled={isExpanding}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              handleQuickSend();
            }
          }}
        />
        <Button onClick={handleQuickSend} size="sm" className="w-8 h-8 p-0 btn-nova">
          {state.draftMessage.trim() ? <Send size={12} /> : <Maximize2 size={12} />}
        </Button>
      </div>
    </motion.div>
  );
}
