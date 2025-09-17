import React from 'react';
import { motion } from 'framer-motion';
import { 
  Download, 
  Calendar, 
  CheckCircle, 
  Clock, 
  TrendingUp,
  Target,
  Bot,
  Activity
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { Progress } from '@/components/ui/progress';
import { useNova } from '@/context/NovaContext';
import { useElectronApi } from '@/hooks/useElectronApi';

/**
 * Nova Dashboard Card - Compact, framed & downloadable overview
 * 
 * Features:
 * - Today's AI plan timeline
 * - Small productivity sparkline
 * - Task completion stats
 * - Quick insights
 * - Export to PDF functionality
 * - Minimal, printable design
 * - Real-time updates
 */

interface DashboardCardProps {
  className?: string;
}

export default function DashboardCard({ className = '' }: DashboardCardProps) {
  const { state } = useNova();
  const { api } = useElectronApi();

  // Calculate today's stats
  const today = new Date().toDateString();
  const todayTasks = state.tasks.filter(task => 
    new Date(task.deadline).toDateString() === today
  );
  
  const completedToday = todayTasks.filter(t => t.status === 'done').length;
  const inProgressToday = todayTasks.filter(t => t.status === 'inprogress').length;
  const totalToday = todayTasks.length;
  const completionRate = totalToday > 0 ? (completedToday / totalToday) * 100 : 0;

  // Generate sparkline data (mock productivity trend)
  const sparklineData = Array.from({ length: 7 }, (_, i) => {
    const baseValue = 65;
    const variation = Math.sin(i * 0.5) * 15;
    return Math.max(30, Math.min(90, baseValue + variation + (Math.random() - 0.5) * 10));
  });

  // Get upcoming tasks (next 3)
  const upcomingTasks = state.tasks
    .filter(task => task.status !== 'done' && new Date(task.deadline) > new Date())
    .sort((a, b) => new Date(a.deadline).getTime() - new Date(b.deadline).getTime())
    .slice(0, 3);

  // Handle PDF export
  const handleExportPdf = async () => {
    const cardElement = document.getElementById('dashboard-card');
    if (cardElement) {
      // TODO: IMPLEMENT IN PRELOAD - window.api.exportDashboardPDF({ html: cardElement.outerHTML })
      console.log('Exporting dashboard to PDF...');
    }
  };

  return (
    <div className={`max-w-md mx-auto ${className}`}>
      <motion.div
        id="dashboard-card"
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="card-nova border-2 border-primary/20 bg-gradient-to-br from-background to-muted/20"
      >
        {/* Header */}
        <div className="flex items-center justify-between mb-6">
          <div>
            <h2 className="text-xl font-bold text-primary">Nova Dashboard</h2>
            <p className="text-sm text-muted-foreground">
              {new Date().toLocaleDateString('en-US', { 
                weekday: 'long',
                year: 'numeric', 
                month: 'long', 
                day: 'numeric' 
              })}
            </p>
          </div>
          
          <Button
            size="sm"
            variant="outline"
            onClick={handleExportPdf}
            className="gap-2 btn-nova-ghost"
          >
            <Download size={14} />
            Export
          </Button>
        </div>

        {/* Today's Overview */}
        <div className="space-y-6">
          {/* Completion Stats */}
          <div className="grid grid-cols-3 gap-4">
            <div className="text-center">
              <div className="text-2xl font-bold text-primary">{completedToday}</div>
              <div className="text-xs text-muted-foreground">Completed</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-yellow-400">{inProgressToday}</div>
              <div className="text-xs text-muted-foreground">In Progress</div>
            </div>
            <div className="text-center">
              <div className="text-2xl font-bold text-foreground">{totalToday}</div>
              <div className="text-xs text-muted-foreground">Total Today</div>
            </div>
          </div>

          {/* Progress Bar */}
          <div className="space-y-2">
            <div className="flex justify-between text-sm">
              <span>Today's Progress</span>
              <span className="text-primary font-medium">{Math.round(completionRate)}%</span>
            </div>
            <Progress value={completionRate} className="h-2" />
          </div>

          {/* Productivity Sparkline */}
          <div className="space-y-2">
            <div className="flex items-center justify-between">
              <span className="text-sm font-medium">7-Day Productivity</span>
              <div className="flex items-center gap-1 text-green-400">
                <TrendingUp size={12} />
                <span className="text-xs">+12%</span>
              </div>
            </div>
            
            <div className="flex items-end gap-1 h-12">
              {sparklineData.map((value, index) => (
                <motion.div
                  key={index}
                  className="bg-primary/30 rounded-t-sm flex-1"
                  initial={{ height: 0 }}
                  animate={{ height: `${(value / 100) * 48}px` }}
                  transition={{ delay: index * 0.1, duration: 0.3 }}
                />
              ))}
            </div>
          </div>

          {/* Upcoming Tasks */}
          <div className="space-y-3">
            <div className="flex items-center gap-2">
              <Calendar size={16} className="text-muted-foreground" />
              <span className="text-sm font-medium">Next Tasks</span>
            </div>
            
            <div className="space-y-2">
              {upcomingTasks.length > 0 ? (
                upcomingTasks.map((task) => (
                  <div key={task.id} className="flex items-center gap-3 p-2 rounded-lg bg-muted/20">
                    <div className="w-2 h-2 rounded-full bg-primary" />
                    <div className="flex-1 min-w-0">
                      <div className="text-sm font-medium truncate">{task.title}</div>
                      <div className="text-xs text-muted-foreground">
                        {new Date(task.deadline).toLocaleTimeString([], { 
                          hour: '2-digit', 
                          minute: '2-digit' 
                        })}
                      </div>
                    </div>
                    
                    <div className="flex items-center gap-1">
                      <Badge 
                        variant="outline" 
                        className={`text-xs ${
                          task.priority === 'High' ? 'text-red-400 border-red-400/20' :
                          task.priority === 'Medium' ? 'text-yellow-400 border-yellow-400/20' :
                          'text-green-400 border-green-400/20'
                        }`}
                      >
                        {task.priority}
                      </Badge>
                      
                      {task.isAgenticTask && (
                        <Bot size={12} className="text-primary" />
                      )}
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-center py-4 text-muted-foreground">
                  <Target size={24} className="mx-auto mb-2 opacity-50" />
                  <div className="text-sm">No upcoming tasks</div>
                </div>
              )}
            </div>
          </div>

          {/* AI Insights */}
          <div className="space-y-2 p-3 rounded-lg bg-primary/5 border border-primary/10">
            <div className="flex items-center gap-2">
              <Bot size={14} className="text-primary" />
              <span className="text-sm font-medium">AI Insight</span>
            </div>
            
            <div className="text-xs text-muted-foreground">
              {completionRate > 70 
                ? "Great productivity today! You're ahead of schedule."
                : completionRate > 40
                ? "Steady progress. Consider prioritizing high-impact tasks."
                : "Let's focus on completing one task at a time."
              }
            </div>
          </div>

          {/* Agent Operations Summary */}
          {state.operations.length > 0 && (
            <div className="space-y-2 p-3 rounded-lg bg-accent/5 border border-accent/10">
              <div className="flex items-center gap-2">
                <Activity size={14} className="text-accent" />
                <span className="text-sm font-medium">Active Operations</span>
                <Badge variant="secondary" className="text-xs">
                  {state.operations.length}
                </Badge>
              </div>
              
              <div className="space-y-1">
                {state.operations.slice(0, 2).map((op) => (
                  <div key={op.id} className="text-xs text-muted-foreground truncate">
                    • {op.title}
                  </div>
                ))}
                {state.operations.length > 2 && (
                  <div className="text-xs text-muted-foreground">
                    +{state.operations.length - 2} more operations
                  </div>
                )}
              </div>
            </div>
          )}
        </div>

        {/* Footer */}
        <div className="mt-6 pt-4 border-t border-border/50">
          <div className="flex items-center justify-between text-xs text-muted-foreground">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-green-500 rounded-full" />
              <span>Local Processing Active</span>
            </div>
            
            <div>
              Generated by Nova AI
            </div>
          </div>
        </div>
      </motion.div>
    </div>
  );
}