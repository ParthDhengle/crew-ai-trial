import React from 'react';
import { motion } from 'framer-motion';
import { 
  Minimize2, 
  Maximize2, 
  X, 
  Square,
  Circle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { useWindowControls } from '@/hooks/useElectronApi';

interface WindowTitleBarProps {
  title?: string;
  className?: string;
}

export default function WindowTitleBar({ 
  title = "Nova AI Assistant",
  className = ""
}: WindowTitleBarProps) {
  const { minimize, maximize, close } = useWindowControls();

  return (
    <div 
      className={`flex items-center justify-between px-4 py-2 bg-background/95 backdrop-blur-sm border-b border-border/50 ${className}`}
      style={{ 
        WebkitAppRegion: 'drag',
        userSelect: 'none'
      }}
    >
      {/* Title */}
      <div className="flex items-center space-x-2">
        <div className="w-2 h-2 bg-red-500 rounded-full" />
        <div className="w-2 h-2 bg-yellow-500 rounded-full" />
        <div className="w-2 h-2 bg-green-500 rounded-full" />
        <span className="ml-3 text-sm font-medium text-foreground/80">
          {title}
        </span>
      </div>

      {/* Window Controls */}
      <div className="flex items-center space-x-1" style={{ WebkitAppRegion: 'no-drag' }}>
        <Button
          size="sm"
          variant="ghost"
          onClick={minimize}
          className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
          title="Minimize"
        >
          <Minimize2 size={12} />
        </Button>
        
        <Button
          size="sm"
          variant="ghost"
          onClick={maximize}
          className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
          title="Maximize"
        >
          <Square size={12} />
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
  );
}
