import React, { useEffect } from 'react';
import { useNova } from '@/context/NovaContext';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import { motion } from 'framer-motion';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import FullChat from './FullChat';
import SchedulerKanban from './SchedulerKanban';
import DashboardCard from './DashboardCard';
import Settings from './Settings';
import AgentOpsPanel from './AgentOpsPanel';

interface MainLayoutProps {
  children?: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const { state, dispatch } = useNova();

  // NEW: Log mount for stability
  useEffect(() => {
    console.log('MAIN LAYOUT: Mounted and stable');
  }, []);

  const toggleSidebar = () => {
    dispatch({ type: 'SET_SIDEBAR_COLLAPSED', payload: !state.sidebarCollapsed });
  };

  const renderContent = () => {
    switch (state.view) {
      case 'chat':
        return <FullChat showAgentOps={true} />;
      case 'scheduler':
        return <SchedulerKanban />;
      case 'dashboard':
        return (
          <div className="min-h-screen flex items-center justify-center p-6 bg-background">
            <DashboardCard />
          </div>
        );
      case 'settings':
        return <Settings />;
      default:
        return <FullChat showAgentOps={true} />;
    }
  };

  return (
    <div className="flex flex-col h-screen bg-background text-foreground">
      <Topbar showSearch={state.view === 'chat'}>
        <Button
          size="sm"
          variant="ghost"
          onClick={toggleSidebar}
          className="ml-2 w-8 h-8 p-0"
        >
          <Menu size={16} />
        </Button>
      </Topbar>

      <div className="flex flex-1 overflow-hidden">
        <motion.div
          initial={{ x: state.sidebarCollapsed ? -250 : 0 }}
          animate={{ x: state.sidebarCollapsed ? -250 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="shrink-0 border-r border-border"
        >
          <Sidebar />
        </motion.div>

        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto">
            {renderContent()}
          </div>
          
          {['chat', 'scheduler'].includes(state.view) && (
            <motion.div
              initial={{ x: 300 }}
              animate={{ x: 0 }}
              transition={{ type: 'spring', stiffness: 300, damping: 30 }}
              className="w-80 shrink-0 border-l border-border"
            >
              <AgentOpsPanel />
            </motion.div>
          )}
        </div>
      </div>
    </div>
  );
}