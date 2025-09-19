import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Mic, 
  MicOff, 
  Paperclip, 
  FileText,
  Smile,
  X,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { Badge } from '@/components/ui/badge';
import { useNova } from '@/context/NovaContext';
import { useVoiceTranscription } from '@/hooks/useElectronApi';
import type { ChatMessage } from '@/api/types';
import { useAuth } from '@/hooks/useAuth';

interface ComposerProps {
  className?: string;
  placeholder?: string;
  maxLength?: number;
}

export default function Composer({ 
  className = '',
  placeholder = 'Message Nova...',
  maxLength = 4000 
}: ComposerProps) {
  const { state, dispatch } = useNova();
  const { idToken, user } = useAuth();
  const [attachments, setAttachments] = useState<File[]>([]);
  const [showRolePrefills, setShowRolePrefills] = useState(false);
  
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const fileInputRef = useRef<HTMLInputElement>(null);
  
  const {
    isRecording,
    transcript,
    isPartial,
    startRecording,
    stopRecording,
  } = useVoiceTranscription();

  // Update message when transcript changes
  useEffect(() => {
    if (transcript && !isPartial) {
      dispatch({
        type: 'SET_DRAFT',
        payload: state.draftMessage + (state.draftMessage ? ' ' : '') + transcript
      });
    }
  }, [transcript, isPartial, state.draftMessage, dispatch]);

  // Auto-resize textarea
  useEffect(() => {
  const textarea = textareaRef.current;
  if (textarea) {
    textarea.style.height = 'auto';
    textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
  }
}, [state.draftMessage]);


  // Handle message sending (real API call)
  const handleSend = async () => {
    if (!state.draftMessage.trim() && attachments.length === 0) return;
  
  const newMessage: ChatMessage = {
    id: `msg-${Date.now()}`,
    content: state.draftMessage.trim(),
    role: 'user',
    timestamp: Date.now(),
  };

    if (state.currentSession) {
      dispatch({ 
        type: 'ADD_MESSAGE', 
        payload: { sessionId: state.currentSession.id, message: newMessage }
      });
    }

    dispatch({ type: 'SET_DRAFT', payload: '' });  // Clear draft
    setAttachments([]);
    dispatch({ type: 'SET_TYPING', payload: true });

    try {
      // ✅ Call FastAPI backend
      const response = await fetch("http://127.0.0.1:8000/process_query", {
        method: "POST",
        headers: {
          "Content-Type": "application/json",
          "Authorization": `Bearer ${idToken}`,  // ✅ Firebase token for auth
        },
        body: JSON.stringify({
          query: newMessage.content,
          session_id: state.currentSession?.id || null,
        }),
      });

      if (!response.ok) {
        throw new Error(`Backend error: ${response.status}`);
      }

      const data = await response.json();

      const aiMessage: ChatMessage = {
        id: `msg-${Date.now()}-ai`,
        content: data.result || "No response received",
        role: 'assistant',
        timestamp: Date.now(),
      };

      if (state.currentSession) {
        dispatch({
          type: 'ADD_MESSAGE',
          payload: { sessionId: state.currentSession.id, message: aiMessage }
        });
      }
    } catch (error) {
      console.error('Failed to send message:', error);
      const errorMsg: ChatMessage = {
        id: `msg-${Date.now()}-error`,
        content: '⚠️ Sorry, something went wrong. Please try again.',
        role: 'assistant',
        timestamp: Date.now(),
      };
      if (state.currentSession) {
        dispatch({ type: 'ADD_MESSAGE', payload: { sessionId: state.currentSession.id, message: errorMsg } });
      }
    } finally {
      dispatch({ type: 'SET_TYPING', payload: false });
    }
  };

  // File select
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setAttachments(prev => [...prev, ...files].slice(0, 5));
  };

  // Remove attachment
  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  // Shortcuts
  const handleKeyDown = (event: React.KeyboardEvent) => {
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSend();
    }
    if (event.key === 'Escape') {
      dispatch({ type: 'SET_DRAFT', payload: '' });
      setAttachments([]);
    }
  };

  // Voice toggle
  const handleVoiceToggle = () => {
    if (isRecording) {
      stopRecording();
    } else {
      startRecording();
    }
  };

  return (
    <div className={`p-4 bg-background/80 backdrop-blur-sm ${className}`}>
      <div className="max-w-4xl mx-auto">
        {/* Voice Transcript */}
        <AnimatePresence>
          {isRecording && transcript && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4 p-3 glass-nova rounded-lg border border-primary/30"
            >
              <div className="flex items-center gap-2 mb-2">
                <div className="w-2 h-2 bg-red-500 rounded-full animate-pulse" />
                <span className="text-sm font-medium text-primary">Recording</span>
                <Badge variant="outline" className="text-xs">
                  {isPartial ? 'Partial' : 'Complete'}
                </Badge>
              </div>
              <div className="text-sm">{transcript || 'Listening...'}</div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Attachments */}
        <AnimatePresence>
          {attachments.length > 0 && (
            <motion.div
              initial={{ opacity: 0, height: 0 }}
              animate={{ opacity: 1, height: 'auto' }}
              exit={{ opacity: 0, height: 0 }}
              className="mb-4"
            >
              <div className="flex flex-wrap gap-2">
                {attachments.map((file, index) => (
                  <motion.div
                    key={index}
                    initial={{ scale: 0 }}
                    animate={{ scale: 1 }}
                    exit={{ scale: 0 }}
                    className="flex items-center gap-2 bg-muted/50 rounded-lg px-3 py-2 text-sm"
                  >
                    <FileText size={14} />
                    <span className="truncate max-w-32">{file.name}</span>
                    <Button
                      size="sm"
                      variant="ghost"
                      onClick={() => removeAttachment(index)}
                      className="w-4 h-4 p-0 hover:bg-destructive/20"
                    >
                      <X size={10} />
                    </Button>
                  </motion.div>
                ))}
              </div>
            </motion.div>
          )}
        </AnimatePresence>

        {/* Input Area */}
        <div className="glass-nova rounded-2xl border border-border/50 focus-within:border-primary/50 transition-colors">
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={state.draftMessage}
              onChange={(e) => dispatch({ type: 'SET_DRAFT', payload: e.target.value })}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="min-h-[60px] max-h-[150px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed px-4 py-3"
              maxLength={maxLength}
            />
          </div>

          <div className="flex items-center justify-between p-3 border-t border-border/30">
            <div className="flex items-center gap-1">
              <Button
                size="sm"
                variant="ghost"
                onClick={() => fileInputRef.current?.click()}
                className="w-8 h-8 p-0"
                aria-label="Attach file"
              >
                <Paperclip size={16} />
              </Button>
              {state.voiceEnabled && (
                <Button
                  size="sm"
                  variant={isRecording ? 'destructive' : 'ghost'}
                  onClick={handleVoiceToggle}
                  className={`w-8 h-8 p-0 ${isRecording ? 'animate-pulse' : ''}`}
                  aria-label={isRecording ? 'Stop recording' : 'Start recording'}
                >
                  {isRecording ? <MicOff size={16} /> : <Mic size={16} />}
                </Button>
              )}
            </div>

            <Button
              onClick={handleSend}
              disabled={!state.draftMessage.trim() && attachments.length === 0}
              className="btn-nova gap-2"
              size="sm"
            >
              {state.isTyping ? (
                <>
                  <Loader2 size={16} className="animate-spin" />
                  <span>Sending...</span>
                </>
              ) : (
                <>
                  <Send size={16} />
                  <span>Send</span>
                </>
              )}
            </Button>
          </div>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          accept=".txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif"
        />

        {/* Quick Tips */}
        <div className="flex items-center justify-center mt-3 text-xs text-muted-foreground gap-4">
          <span>Ctrl+Enter to send</span>
          <span>•</span>
          <span>Escape to clear</span>
          <span>•</span>
          <span className="flex items-center gap-1">
            <div className="w-2 h-2 bg-green-500 rounded-full" />
            Local voice processing
          </span>
        </div>

        {/* Hidden File Input */}
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={handleFileSelect}
          accept=".txt,.pdf,.doc,.docx,.jpg,.jpeg,.png,.gif"
        />
      </div>
    </div>
  );
}