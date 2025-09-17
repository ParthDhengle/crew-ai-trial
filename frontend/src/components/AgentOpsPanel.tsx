// frontend/src/components/AgentOpsPanel.tsx
import React from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { 
  Bot, 
  X, 
  Clock, 
  CheckCircle, 
  AlertCircle, 
  Loader2,
  ChevronUp,
  ChevronDown,
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Progress } from '@/components/ui/progress';
import { ScrollArea } from '@/components/ui/scroll-area';
import { Badge } from '@/components/ui/badge';
import { useNova } from '@/context/NovaContext';
import type { AgentOp } from '@/api/types';

interface AgentOpsPanelProps {
  className?: string;
  collapsible?: boolean;
}

export default function AgentOpsPanel({ 
  className = '',
  collapsible = true 
}: AgentOpsPanelProps) {
  const { state } = useNova();  // ✅ Real operations from Firestore
  const operations = state.operations || [];
  const [isCollapsed, setIsCollapsed] = React.useState(false);

  // Status icon + color
  const getStatusDisplay = (status: AgentOp['status']) => {
    switch (status) {
      case 'pending':
        return { icon: Clock, color: 'text-yellow-400', bgColor: 'bg-yellow-400/10', label: 'Pending' };
      case 'running':
        return { icon: Loader2, color: 'text-primary animate-spin', bgColor: 'bg-primary/10', label: 'Running' };
      case 'success':
        return { icon: CheckCircle, color: 'text-green-400', bgColor: 'bg-green-400/10', label: 'Success' };
      case 'failed':
        return { icon: AlertCircle, color: 'text-red-400', bgColor: 'bg-red-400/10', label: 'Failed' };
      default:
        return { icon: Clock, color: 'text-muted-foreground', bgColor: 'bg-muted/10', label: 'Unknown' };
    }
  };

  // Format elapsed time
  const formatElapsedTime = (startTime?: number) => {
    if (!startTime) return '0s';
    const elapsed = Date.now() - startTime;
    const seconds = Math.floor(elapsed / 1000);
    const minutes = Math.floor(seconds / 60);
    return minutes > 0 ? `${minutes}m ${seconds % 60}s` : `${seconds}s`;
  };

  // Cancel handler (call API if needed)
  const handleCancel = async (operationId: string) => {
    // If you have a Firestore action, call it here:
    // await updateOperationStatus(operationId, 'cancelled');
    console.log(`Cancel op ${operationId}`);
  };

  // Empty state
  if (operations.length === 0) {
    return (
      <div className={`w-full h-full flex flex-col bg-background/50 ${className}`}>
        <div className="p-4 border-b border-border">
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-primary" />
            <span className="font-medium text-sm">Agent Operations</span>
          </div>
        </div>
        
        <div className="flex-1 flex items-center justify-center text-center p-6">
          <div className="space-y-3">
            <Bot size={32} className="mx-auto text-muted-foreground opacity-50" />
            <div className="text-sm text-muted-foreground">No active operations</div>
            <div className="text-xs text-muted-foreground">Agent tasks will appear here when running</div>
          </div>
        </div>
      </div>
    );
  }

  return (
    <motion.div 
      className={`w-full h-full flex flex-col bg-background/50 ${className}`}
      initial={{ opacity: 0, x: 20 }}
      animate={{ opacity: 1, x: 0 }}
      transition={{ duration: 0.3 }}
    >
      {/* Header */}
      <div className="p-4 border-b border-border">
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            <Bot size={16} className="text-primary" />
            <span className="font-medium text-sm">Agent Operations</span>
            <Badge variant="secondary" className="text-xs">{operations.length}</Badge>
          </div>
          {collapsible && (
            <Button
              size="sm"
              variant="ghost"
              onClick={() => setIsCollapsed(!isCollapsed)}
              className="w-6 h-6 p-0"
            >
              {isCollapsed ? <ChevronUp size={12} /> : <ChevronDown size={12} />}
            </Button>
          )}
        </div>
      </div>

      {/* List */}
      <AnimatePresence>
        {!isCollapsed && (
          <motion.div
            initial={{ height: 0 }}
            animate={{ height: 'auto' }}
            exit={{ height: 0 }}
            className="flex-1 overflow-hidden"
          >
            <ScrollArea className="h-full">
              <div className="p-4 space-y-3">
                {operations.map((op, index) => {
                  const statusDisplay = getStatusDisplay(op.status);
                  const StatusIcon = statusDisplay.icon;
                  return (
                    <motion.div
                      key={op.id}
                      initial={{ opacity: 0, y: 20 }}
                      animate={{ opacity: 1, y: 0 }}
                      exit={{ opacity: 0, y: -20 }}
                      transition={{ delay: index * 0.1 }}
                      className={`card-nova p-4 ${statusDisplay.bgColor} border border-white/5`}
                    >
                      {/* Header */}
                      <div className="flex items-start justify-between mb-3">
                        <div className="flex items-start gap-3 flex-1 min-w-0">
                          <div className={`mt-0.5 ${statusDisplay.color}`}>
                            <StatusIcon size={16} />
                          </div>
                          <div className="flex-1 min-w-0">
                            <div className="font-medium text-sm truncate">{op.title}</div>
                            {op.desc && <div className="text-xs text-muted-foreground mt-1 line-clamp-2">{op.desc}</div>}
                            <div className="flex items-center gap-3 mt-2 text-xs text-muted-foreground">
                              <Badge variant="outline" className={`${statusDisplay.color} border-current`}>
                                {statusDisplay.label}
                              </Badge>
                              <span className="flex items-center gap-1">
                                <Clock size={10} /> {formatElapsedTime(op.startTime)}
                              </span>
                            </div>
                          </div>
                        </div>
                        {(op.status === 'pending' || op.status === 'running') && (
                          <Button
                            size="sm"
                            variant="ghost"
                            onClick={() => handleCancel(op.id)}
                            className="w-6 h-6 p-0 text-muted-foreground hover:text-destructive shrink-0"
                          >
                            <X size={12} />
                          </Button>
                        )}
                      </div>

                      {/* Progress */}
                      {op.status === 'running' && typeof op.progress === 'number' && (
                        <div className="space-y-1">
                          <div className="flex justify-between text-xs">
                            <span className="text-muted-foreground">Progress</span>
                            <span className="text-primary font-medium">{op.progress}%</span>
                          </div>
                          <Progress value={op.progress} className="h-2 bg-white/5" />
                        </div>
                      )}
                    </motion.div>
                  );
                })}
              </div>
            </ScrollArea>
          </motion.div>
        )}
      </AnimatePresence>

      {/* Footer Stats */}
      <div className="p-4 border-t border-border bg-background/80">
        <div className="grid grid-cols-3 gap-4 text-center">
          <div>
            <div className="text-xs text-muted-foreground">Active</div>
            <div className="text-sm font-medium text-primary">
              {operations.filter(op => op.status === 'running').length}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Queued</div>
            <div className="text-sm font-medium text-yellow-400">
              {operations.filter(op => op.status === 'pending').length}
            </div>
          </div>
          <div>
            <div className="text-xs text-muted-foreground">Completed</div>
            <div className="text-sm font-medium text-green-400">
              {operations.filter(op => op.status === 'success').length}
            </div>
          </div>
        </div>
      </div>
    </motion.div>
  );
}
