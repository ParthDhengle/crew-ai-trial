import React, { useState, useRef, useEffect } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Send, 
  Mic, 
  MicOff, 
  Paperclip, 
  Image,
  FileText,
  Smile,
  X,
  Loader2
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Textarea } from '@/components/ui/textarea';
import { 
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select';
import { 
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { useNova } from '@/context/NovaContext';
import { useVoiceTranscription } from '@/hooks/useElectronApi';
import { chatService } from '@/api/chatService';
import type { ChatMessage } from '@/api/types';

/**
 * Nova Composer - Text and voice input component
 * 
 * Features:
 * - Multi-line text input with markdown support
 * - Voice transcription (local Whisper)
 * - File attachments
 * - Role prefills and quick actions
 * - Streaming voice-to-text display
 * - Auto-resize textarea
 * - Keyboard shortcuts (Ctrl+Enter to send)
 * - Real-time character count
 */

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
  const [message, setMessage] = useState('');
  const [attachments, setAttachments] = useState<File[]>([]);
  const [isTyping, setIsTyping] = useState(false);
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
      setMessage(prev => prev + (prev ? ' ' : '') + transcript);
    }
  }, [transcript, isPartial]);

  // Auto-resize textarea
  useEffect(() => {
    const textarea = textareaRef.current;
    if (textarea) {
      textarea.style.height = 'auto';
      textarea.style.height = `${Math.min(textarea.scrollHeight, 150)}px`;
    }
  }, [message]);

  // Role-based message prefills
  const rolePrefills = {
    friend: [
      "Hey Nova, I need some advice about...",
      "Can you help me think through...",
      "What do you think about...",
    ],
    mentor: [
      "I'm looking for guidance on...",
      "Can you help me develop a plan for...",
      "What steps should I take to...",
    ],
    girlfriend: [
      "I've been thinking about us and...",
      "How was your day? I want to tell you about...",
      "I love talking to you about...",
    ],
    husband: [
      "Let's plan something special...",
      "I need your support with...",
      "Can we discuss our goals for...",
    ],
    guide: [
      "Please analyze and provide recommendations for...",
      "I need a structured approach to...",
      "Create a comprehensive plan for...",
    ],
  };

  // Handle message sending
  const handleSend = async () => {
    if (!message.trim() && attachments.length === 0) return;
    
    const messageContent = message.trim();
    
    // Clear input immediately
    setMessage('');
    setAttachments([]);
    
    try {
      // Send message through chat service
      await chatService.sendMessage(messageContent, state.currentSession?.id);
    } catch (error) {
      console.error('Failed to send message:', error);
      // Show error message to user
      const errorMessage: ChatMessage = {
        id: `error-${Date.now()}`,
        content: 'Sorry, I encountered an error processing your message. Please try again.',
        role: 'system',
        timestamp: Date.now(),
      };
      
      if (state.currentSession) {
        dispatch({ 
          type: 'ADD_MESSAGE', 
          payload: { sessionId: state.currentSession.id, message: errorMessage }
        });
      }
    }
  };

  // Handle file attachments
  const handleFileSelect = (event: React.ChangeEvent<HTMLInputElement>) => {
    const files = Array.from(event.target.files || []);
    setAttachments(prev => [...prev, ...files].slice(0, 5)); // Max 5 files
  };

  // Remove attachment
  const removeAttachment = (index: number) => {
    setAttachments(prev => prev.filter((_, i) => i !== index));
  };

  // Handle keyboard shortcuts
  const handleKeyDown = (event: React.KeyboardEvent) => {
    // Ctrl/Cmd + Enter to send
    if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') {
      event.preventDefault();
      handleSend();
    }
    
    // Escape to clear
    if (event.key === 'Escape') {
      setMessage('');
      setAttachments([]);
    }
  };

  // Handle voice recording toggle
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
        {/* Voice Transcript Display */}
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
              <div className="text-sm">
                {transcript || 'Listening...'}
              </div>
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

        {/* Main Input Area */}
        <div className="glass-nova rounded-2xl border border-border/50 focus-within:border-primary/50 transition-colors">
          {/* Role Prefills */}
          <AnimatePresence>
            {showRolePrefills && (
              <motion.div
                initial={{ height: 0 }}
                animate={{ height: 'auto' }}
                exit={{ height: 0 }}
                className="border-b border-border/30 overflow-hidden"
              >
                <div className="p-3">
                  <div className="text-xs text-muted-foreground mb-2">
                    Quick {state.role} prompts:
                  </div>
                  <div className="space-y-1">
                    {rolePrefills[state.role].map((prefill, index) => (
                      <Button
                        key={index}
                        size="sm"
                        variant="ghost"
                        className="text-xs h-6 justify-start font-normal text-left"
                        onClick={() => {
                          setMessage(prefill);
                          setShowRolePrefills(false);
                          textareaRef.current?.focus();
                        }}
                      >
                        {prefill}
                      </Button>
                    ))}
                  </div>
                </div>
              </motion.div>
            )}
          </AnimatePresence>

          {/* Textarea */}
          <div className="relative">
            <Textarea
              ref={textareaRef}
              value={message}
              onChange={(e) => setMessage(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder={placeholder}
              className="min-h-[60px] max-h-[150px] resize-none border-0 bg-transparent focus-visible:ring-0 focus-visible:ring-offset-0 text-base leading-relaxed px-4 py-3"
              maxLength={maxLength}
            />

            {/* Character Count */}
            {message.length > maxLength * 0.8 && (
              <div className="absolute bottom-2 right-2 text-xs text-muted-foreground">
                {message.length}/{maxLength}
              </div>
            )}
          </div>

          {/* Controls */}
          <div className="flex items-center justify-between p-3 border-t border-border/30">
            <div className="flex items-center gap-1">
              {/* Attachments */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => fileInputRef.current?.click()}
                className="w-8 h-8 p-0"
                aria-label="Attach file"
              >
                <Paperclip size={16} />
              </Button>

              {/* Role Prefills Toggle */}
              <Button
                size="sm"
                variant="ghost"
                onClick={() => setShowRolePrefills(!showRolePrefills)}
                className="w-8 h-8 p-0"
                aria-label="Show role prefills"
              >
                <Smile size={16} />
              </Button>

              {/* Voice Recording */}
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

            {/* Send Button */}
            <Button
              onClick={handleSend}
              disabled={!message.trim() && attachments.length === 0}
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