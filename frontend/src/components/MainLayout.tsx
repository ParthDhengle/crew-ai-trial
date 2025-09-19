import React from 'react';
import { useNova } from '@/context/NovaContext';
import Sidebar from './Sidebar';
import Topbar from './Topbar';
import WindowTitleBar from './WindowTitleBar';
import { motion } from 'framer-motion';
import { Menu } from 'lucide-react';
import { Button } from '@/components/ui/button';
import FullChat from './FullChat';
import SchedulerKanban from './SchedulerKanban';
import DashboardCard from './DashboardCard';
import Settings from './Settings';
import AgentOpsPanel from './AgentOpsPanel';

/**
 * MainLayout - Single source for Topbar/sidebar across views
 */
interface MainLayoutProps {
  children?: React.ReactNode;
}

export default function MainLayout({ children }: MainLayoutProps) {
  const { state, dispatch } = useNova();

  // Toggle sidebar via hamburger
  const toggleSidebar = () => {
    dispatch({ type: 'SET_SIDEBAR_COLLAPSED', payload: !state.sidebarCollapsed });
  };

  // Render content based on view (pure content—no layout dups)
  const renderContent = () => {
    switch (state.view) {
      case 'chat':
        return <FullChat showAgentOps={true} />; // Pure chat, no sidebar/Topbar
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
    <div className="flex flex-col h-screen bg-background text-foreground overflow-hidden">
      {/* Window Title Bar */}
      <WindowTitleBar title="Nova AI Assistant" />
      
      {/* Single Topbar with Hamburger */}
      <Topbar showSearch={state.view === 'chat'}>
        {/* Hamburger - Always present */}
        <Button
          size="sm"
          variant="ghost"
          onClick={toggleSidebar}
          className="ml-2 w-8 h-8 p-0" // Show always, not just lg:hidden
        >
          <Menu size={16} />
        </Button>
      </Topbar>

      {/* Sidebar + Main Content */}
      <div className="flex flex-1 overflow-hidden">
        {/* Collapsible Sidebar */}
        <motion.div
          initial={{ x: state.sidebarCollapsed ? -250 : 0 }}
          animate={{ x: state.sidebarCollapsed ? -250 : 0 }}
          transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          className="shrink-0 border-r border-border"
        >
          <Sidebar />
        </motion.div>

        {/* Main Content Area */}
        <div className="flex-1 flex flex-col overflow-hidden">
          <div className="flex-1 overflow-auto">
            {renderContent()}
          </div>
          
          {/* Agent Ops Panel - Only in chat/scheduler */}
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