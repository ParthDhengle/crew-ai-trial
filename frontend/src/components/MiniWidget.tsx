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
  Minus  // Added for close functionality
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
import { chatService } from '@/api/chatService';
interface MiniWidgetProps {
  className?: string;
  unreadCount?: number;
}

export default function MiniWidget({
  className = '',
  unreadCount = 0
}: MiniWidgetProps) {
  const [isHovered, setIsHovered] = useState(false);
  const [miniMessage, setMiniMessage] = useState('');
  const [showMenu, setShowMenu] = useState(false);
  const [isExpanding, setIsExpanding] = useState(false);
  const scrollRef = useRef<HTMLDivElement>(null);
  const { expand, close, minimize } = useWindowControls();
  const { state, dispatch } = useNova();

  // Last 3 messages for preview
  const previewMessages = state.currentSession?.messages.slice(-3) || [];

  // Handle expand with loading state
  const handleExpand = async () => {
    if (miniMessage.trim()) {
      console.log('Mini send:', miniMessage);
      // Send message before expanding
      try {
        await chatService.sendMessage(miniMessage.trim(), state.currentSession?.id);
        setMiniMessage('');
      } catch (error) {
        console.error('Failed to send message before expand:', error);
      }
    }
    
    setIsExpanding(true);
    try {
      console.log('MINI: Button clicked—awaiting IPC expand...');
      const result = await expand();
      console.log('MINI: IPC expand completed:', result);
      
      // Only proceed if expand was successful
      if (result?.success !== false) {
        // In development, simulate window switch by updating URL
        if (typeof window !== 'undefined') {
          const url = new URL(window.location.href);
          url.searchParams.delete('mini');
          window.history.replaceState({}, '', url.toString());
          // Trigger a re-render by dispatching a state change
          dispatch({ type: 'SET_VIEW', payload: 'chat' });
        }
      }
    } catch (error) {
      console.error('MINI: Expand failed:', error);
    } finally {
      setIsExpanding(false);
    }
  };

  // Handle close
  const handleClose = () => {
    console.log('MINI: Close button clicked');
    // Send specific mini close
    // Send specific mini close event
    if (window.api) {
      // Use electron's ipcRenderer to send mini:close event
      (window as any).api.windowClose?.();
    } else {
      // Fallback for development
      window.close();
    }
  };

  // Handle quick send
  const handleQuickSend = async () => {
    if (!miniMessage.trim()) {
      // If no message, just expand
      await handleExpand();
      return;
    }

    console.log('MINI: Sending quick message:', miniMessage);
    
    const messageContent = miniMessage.trim();
    setMiniMessage('');
    
    try {
      // Send message through chat service
      await chatService.sendMessage(messageContent, state.currentSession?.id);
      // Don't auto-expand after sending - let user choose
      console.log('MINI: Message sent successfully');
    } catch (error) {
      console.error('Failed to send message from mini widget:', error);
      // Show error in mini widget instead of expanding
      const errorMessage = 'Failed to send message. Please try again.';
      // You could add a toast notification here
    }
  };

  useEffect(() => {
    const handleFocus = () => {
      setIsExpanding(false);
    };

    window.addEventListener('focus', handleFocus);
    // Reset on mount
    setIsExpanding(false);

    return () => window.removeEventListener('focus', handleFocus);
  }, []);

  // Auto-scroll preview
  useEffect(() => {
    scrollRef.current?.scrollTo({ 
      top: scrollRef.current.scrollHeight, 
      behavior: 'smooth' 
    });
  }, [previewMessages]);

  return (
    <motion.div
      className={`glass-nova rounded-xl overflow-hidden border border-primary/30 shadow-2xl w-full h-full max-w-full relative ${className}`}
      initial={{ scale: 0.9, opacity: 0, y: 20 }}
      animate={{ scale: 1, opacity: 1, y: 0 }}
      whileHover={{ scale: 1.02 }}
      transition={{ type: 'spring', stiffness: 300 }}
      onMouseEnter={() => setIsHovered(true)}
      onMouseLeave={() => setIsHovered(false)}
    >
      {/* Loading Overlay */}
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

      {/* Window Title Bar */}
        <div 
        className={`flex items-center justify-between px-4 py-2 bg-background/95 backdrop-blur-sm border-b border-border/50 ${className}`}
        style={{ 
          ['WebkitAppRegion' as any]: 'drag',
          userSelect: 'none'
        }}
      >
        {/* Title */}
        <div className="flex items-center space-x-2">
          <span className="ml-3 text-sm font-medium text-foreground/80">
            "Nova Chat Assistant"
          </span>
        </div>

        {/* Window Controls */}
        <div className="flex items-center space-x-1" style={{ ['WebkitAppRegion' as any]: 'no-drag' }}>
          <Button
            size="sm"
            variant="ghost"
            onClick={minimize}
            className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
            title="Minimize"
          >
            <Minus size={12} />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={expand}
            className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
            title="Maximize"
          >
            <Maximize2 size={12} />
          </Button>
          
          <Button
            size="sm"
            variant="ghost"
            onClick={close}
            className="w-6 h-6 p-0 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-none"
            title="Close"
          >
            <X size={12} />
          </Button>
        </div>
      </div>
      
      {/* Mini Widget Status Bar */}
      <div className="flex items-center justify-between px-3 py-2 bg-background/90 border-b border-border/50">
        <div className="flex items-center gap-2">
          <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
          <span className="text-sm font-medium">Chat</span>
          {unreadCount > 0 && (
            <Badge variant="secondary" className="text-xs px-1.5 py-0 min-w-[18px] h-4">
              {unreadCount}
            </Badge>
          )}
        </div>
        
        <div className="flex items-center gap-1">

          {/* Menu */}
          <DropdownMenu open={showMenu} onOpenChange={setShowMenu}>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="w-6 h-6 p-0">
                <MoreVertical size={12} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={handleExpand} disabled={isExpanding}>
                <MessageSquare className="mr-2 h-4 w-4" />
                Full Chat
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

      {/* Messages Preview */}
      <ScrollArea className="flex-1 px-3 py-2 max-w-full" ref={scrollRef}>
        <div className="space-y-2 max-w-full">
          {previewMessages.length === 0 ? (
            <motion.div 
              className="text-center text-xs text-muted-foreground py-8"
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Bot size={24} className="mx-auto mb-2 text-primary/50" />
              <p>Start a conversation!</p>
              <p className="mt-1 text-[10px]">Type below or click expand</p>
            </motion.div>
          ) : (
            <AnimatePresence>
              {previewMessages.map((msg, index) => (
                <motion.div
                  key={msg.id}
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  exit={{ opacity: 0, y: -10 }}
                  transition={{ delay: index * 0.05 }}
                  className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                >
                  <div className={`max-w-[200px] rounded-lg px-2 py-1 text-xs max-w-full break-words ${
                    msg.role === 'user' ? 'bg-primary text-primary-foreground' : 'bg-muted/50 text-muted-foreground border border-border/30'
                  }`}>
                    <div className="flex items-center gap-1 mb-1">
                      <div className="flex items-center gap-1">
                        {msg.role === 'user' ? (
                          <User size={8} />
                        ) : (
                          <Bot size={8} className="text-primary" />
                        )}
                        <span className="font-medium">
                          {msg.role === 'user' ? 'You' : 'Nova'}
                        </span>
                      </div>
                      <span className="text-[10px] opacity-50 ml-auto">
                        {new Date(msg.timestamp).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </span>
                    </div>

                    <div className="whitespace-pre-wrap leading-tight">
                      {typeof msg.content === 'string' ? msg.content : 'Invalid message format'}  {/* Safeguard */}
                    </div>
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          )}

          {/* Typing indicator */}
          {state.isTyping && (
            <motion.div
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex justify-start"
            >
              <div className="bg-muted/50 rounded-lg px-2 py-1 border border-border/30">
                <div className="flex items-center gap-1 text-xs text-muted-foreground">
                  <div className="flex gap-0.5">
                    <div className="w-1 h-1 bg-primary rounded-full animate-pulse" />
                    <div className="w-1 h-1 bg-primary rounded-full animate-pulse delay-75" />
                    <div className="w-1 h-1 bg-primary rounded-full animate-pulse delay-150" />
                  </div>
                  <span>Nova is typing...</span>
                </div>
              </div>
            </motion.div>
          )}
        </div>
      </ScrollArea>

      {/* Mini Input */}
      <div className="border-t border-border/50 p-2 bg-background/50 sticky bottom-0 z-10 flex-shrink-0 max-w-full">
        <div className="flex gap-1">
          <Input
            value={miniMessage}
            onChange={(e) => setMiniMessage(e.target.value)}
            placeholder="Quick message..."
            className="text-xs h-8 flex-1 max-w-full bg-background/70"
            disabled={isExpanding}
            onKeyDown={(e) => {
              if (e.key === 'Enter' && !e.shiftKey) {
                e.preventDefault();
                handleQuickSend();
              }
            }}
          />
          <Button 
            onClick={handleQuickSend} 
            size="sm" 
            className="w-8 h-8 p-0 btn-nova"
            disabled={isExpanding}
            title={miniMessage.trim() ? "Send & Expand" : "Expand Chat"}
          >
            {miniMessage.trim() ? <Send size={12} /> : <Maximize2 size={12} />}
          </Button>
        </div>

        {/* Status indicators */}
        <div className="flex items-center justify-between mt-1 text-xs text-muted-foreground max-w-full">
          <div className="flex items-center gap-2">
            {state.voiceEnabled && (
              <div className="flex items-center gap-1">
                <Mic size={10} />
                <span>Voice ready</span>
              </div>
            )}
            {state.operations.length > 0 && (
              <Badge variant="outline" className="text-[10px] px-1 py-0 bg-primary/10 text-primary border-primary/20">
                {state.operations.length} ops
              </Badge>
            )}
          </div>
          
          <motion.div
            className="text-[10px] opacity-60"
            animate={{ opacity: isHovered ? 1 : 0.6 }}
          >
            Press Enter or click to expand
          </motion.div>
        </div>
      </div>

      {/* Activity pulse if operations are running */}
      {state.operations.length > 0 && (
        <motion.div
          className="absolute inset-0 rounded-xl bg-primary/5 pointer-events-none"
          animate={{ opacity: [0.3, 0.6, 0.3] }}
          transition={{ duration: 2, repeat: Infinity }}
        />
      )}
    </motion.div>
  );
}

// Keyboard shortcuts handler
export function useMiniWidgetKeyboard() {
  const { expand } = useWindowControls();
  const { dispatch } = useNova();

  useEffect(() => {
    const handleKeyDown = (event: KeyboardEvent) => {
      // Ctrl/Cmd + Space to toggle mini/full
      if ((event.ctrlKey || event.metaKey) && event.code === 'Space') {
        event.preventDefault();
        if (window.api) {
          expand();
        } else {
          dispatch({ type: 'SET_MINI_MODE', payload: false });
        }
      }
      
      // Escape to close
      if (event.code === 'Escape') {
        if (window.api) {
          (window as any).api.windowClose?.();
        }
      }
    };

    document.addEventListener('keydown', handleKeyDown);
    return () => document.removeEventListener('keydown', handleKeyDown);
  }, [expand, dispatch]);
}
