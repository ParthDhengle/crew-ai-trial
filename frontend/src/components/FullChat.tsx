import React, { useState, useRef, useEffect } from 'react';
import { motion } from 'framer-motion';
import {
  Volume2,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { ScrollArea } from '@/components/ui/scroll-area';
import { useNova } from '@/context/NovaContext';
import Composer from './Composer';
import type { ChatMessage, NovaRole } from '@/api/types';
import { useAuth } from '@/context/AuthContext';
/**
 * FullChat - Pure chat content (no layout—use in MainLayout)
 */
interface FullChatProps {
  className?: string;
  showAgentOps?: boolean; // Keep optional for legacy
}

export default function FullChat({
  className = '',
  showAgentOps = true
}: FullChatProps) {
  const { state, dispatch } = useNova();
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const { user } = useAuth();
  // Auto-scroll
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [state.currentSession?.messages]);

  useEffect(() => {
    if (!state.currentSession) {
      // Auto-create if none (handled in context, but fallback)
      const newSession = {
        id: crypto.randomUUID(),
        title: 'Main Chat',
        messages: [],
        createdAt: Date.now(),
        updatedAt: Date.now(),
      };
      dispatch({ type: 'SET_CURRENT_SESSION', payload: newSession });
    }
  }, [state.currentSession]);

  // Message actions
  const handleMessageAction = async (action: { type: string; payload?: any }) => {
    const mockResponse = {
      accept_schedule: 'Schedule accepted and added to your calendar',
      reschedule: 'Rescheduling options prepared',
      send_email: 'Email draft created and ready to send',
      run_operation: 'Operation queued for execution'
    };
    const responseText = mockResponse[action.type as keyof typeof mockResponse] || 'Action completed';
   
    if (state.currentSession) {
      const systemMessage: ChatMessage = {
        id: `system-${Date.now()}`,
        content: responseText,
        role: 'system',
        timestamp: Date.now(),
      };
      dispatch({
        type: 'ADD_MESSAGE',
        payload: { sessionId: state.currentSession.id, message: systemMessage }
      });
    }
  };

  const handleSpeak = async (text: string) => {
    console.log('Speaking text:', text);
  };

  const getRoleGreeting = (role: NovaRole) => {
    const greetings = {
      friend: "Hey there! What's on your mind?",
      mentor: "I'm here to guide and support you. What would you like to work on?",
      girlfriend: "Hi love! How's your day going? 💝",
      husband: "Hey honey, what can I help you with today?",
      guide: "Welcome. I'm here to assist you on your journey. What do you need?"
    };
    return greetings[role];
  };

  return (
    <div className={`flex flex-col h-full bg-background text-foreground ${className}`}>
      {/* Chat Messages - Full height */}
      <div className="flex-1 flex flex-col">
        <ScrollArea className="flex-1 px-6 py-4">
          <div className="max-w-4xl mx-auto space-y-6">
            {/* Welcome Message */}
            {(!state.currentSession?.messages || state.currentSession.messages.length === 0) && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="text-center py-12"
              >
                <div className="w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold text-primary-foreground">
                  N
                </div>
                <h2 className="text-2xl font-bold mb-2">
                  {user
                    ? `Hi ${user.displayName || user.email?.split('@')[0]}, welcome to Nova!!`
                    : "Welcome to Nova"}
                </h2>
                <p className="text-muted-foreground mb-4">
                  {getRoleGreeting(state.role)}
                </p>
                <div className="flex items-center justify-center gap-2 text-sm text-muted-foreground">
                  <Badge variant="outline" className="bg-green-500/10 text-green-400 border-green-500/20">
                    Local Voice Enabled
                  </Badge>
                  <Badge variant="outline" className="bg-primary/10 text-primary border-primary/20">
                    Privacy First
                  </Badge>
                </div>
              </motion.div>
            )}
            {/* Messages */}
            {state.currentSession?.messages?.length > 0 && state.currentSession?.messages.map((message, index) => (
              <motion.div
                key={`${message.id}-${index}`}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: index * 0.05 }}
                className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
              >
                <div className={`max-w-3xl ${message.role === 'user' ? 'order-2' : ''}`}>
                  <div
                    className={`rounded-2xl px-4 py-3 ${
                      message.role === 'user'
                        ? 'bg-primary text-primary-foreground ml-12'
                        : message.role === 'system'
                        ? 'bg-muted/50 text-muted-foreground border border-border'
                        : 'glass-nova glow-nova mr-12'
                    }`}
                  >
                    {/* Role & Time */}
                    <div className="flex items-center justify-between mb-2">
                      <div className="text-xs font-medium opacity-70">
                        {message.role === 'assistant' ? 'Nova' :
                         message.role === 'system' ? 'System' : 'You'}
                      </div>
                      <div className="text-xs opacity-50">
                        {new Date(message.timestamp).toLocaleTimeString()}
                      </div>
                    </div>
                    {/* Content */}
                    <div className="text-sm leading-relaxed whitespace-pre-wrap">
                      {typeof message.content === 'string' 
                        ? message.content 
                        : JSON.stringify(message.content, null, 2)  // Pretty-print object as fallback
                      }
                    </div>
                    {/* Actions */}
                    {message.actions && message.actions.length > 0 && (
                      <div className="flex flex-wrap gap-2 mt-3 pt-3 border-t border-white/10">
                        {message.actions.map((action, actionIndex) => (
                          <Button
                            key={actionIndex}
                            size="sm"
                            variant="secondary"
                            className="h-7 text-xs btn-nova-ghost"
                            onClick={() => handleMessageAction(action)}
                          >
                            {action.label}
                          </Button>
                        ))}
                      </div>
                    )}
                    {/* TTS */}
                    {message.role === 'assistant' && (
                      <div className="flex justify-end mt-2">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-6 w-6 p-0 opacity-50 hover:opacity-100"
                          onClick={() => handleSpeak(message.content)}
                          aria-label="Read aloud"
                        >
                          <Volume2 size={12} />
                        </Button>
                      </div>
                    )}
                  </div>
                </div>
              </motion.div>
            ))}
            {/* Typing Indicator */}
            {state.isTyping && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="flex justify-start"
              >
                <div className="glass-nova rounded-2xl px-4 py-3 mr-12">
                  <div className="flex items-center gap-2 text-muted-foreground">
                    <div className="flex gap-1">
                      <div className="w-2 h-2 bg-primary rounded-full animate-pulse" />
                      <div className="w-2 h-2 bg-primary rounded-full animate-pulse delay-75" />
                      <div className="w-2 h-2 bg-primary rounded-full animate-pulse delay-150" />
                    </div>
                    <span className="text-sm">Nova is thinking...</span>
                  </div>
                </div>
              </motion.div>
            )}
            {/* Scroll anchor */}
            <div ref={messagesEndRef} />
          </div>
        </ScrollArea>
        {/* Composer - At bottom */}
        <div className="border-t border-border">
          <Composer />
        </div>
      </div>
    </div>
  );
}