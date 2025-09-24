import React, { useState, useEffect, useCallback, useRef } from 'react';
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Mail,
  Edit3,
  MoreHorizontal,
  Calendar,
  Flag,
  Bot,
  AlertTriangle,
  Trash2,
} from 'lucide-react';

// Types
interface SchedulerTask {
  id: string;
  title: string;
  description?: string;
  startAt: string; // ISO UTC timestamp
  endAt: string; // ISO UTC timestamp
  date: string; // YYYY-MM-DD local date
  priority: 'High' | 'Medium' | 'Low';
  status: 'pending' | 'completed' | 'cancelled';
  tags?: string[];
  isAgenticTask?: boolean;
  aiSuggested?: boolean;
  createdAt: string;
  updatedAt: string;
}

interface SchedulerKanbanProps {
  apiBase?: string;
}

// Mock data for demonstration
const mockTasks: SchedulerTask[] = [
  {
    id: 'task-1',
    title: 'Team standup meeting',
    description: 'Daily sync with the development team',
    startAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(), // 2 hours from now
    endAt: new Date(Date.now() + 2.5 * 60 * 60 * 1000).toISOString(), // 2.5 hours from now
    date: new Date().toISOString().split('T')[0],
    priority: 'High',
    status: 'pending',
    tags: ['meeting', 'team'],
    isAgenticTask: false,
    aiSuggested: true,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-2',
    title: 'Code review session',
    description: 'Review pull requests for the new feature',
    startAt: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(), // 4 hours from now
    endAt: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(), // 5 hours from now
    date: new Date().toISOString().split('T')[0],
    priority: 'Medium',
    status: 'pending',
    tags: ['development', 'review'],
    isAgenticTask: true,
    aiSuggested: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-3',
    title: 'Lunch break',
    description: 'Time to recharge and refuel',
    startAt: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(), // 6 hours from now
    endAt: new Date(Date.now() + 7 * 60 * 60 * 1000).toISOString(), // 7 hours from now
    date: new Date().toISOString().split('T')[0],
    priority: 'Low',
    status: 'completed',
    tags: ['break', 'personal'],
    isAgenticTask: false,
    aiSuggested: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-4',
    title: 'Project deadline review',
    description: 'Overdue task needs attention',
    startAt: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago (missed)
    endAt: new Date(Date.now() - 1 * 60 * 60 * 1000).toISOString(), // 1 hour ago (missed)
    date: new Date().toISOString().split('T')[0],
    priority: 'High',
    status: 'pending',
    tags: ['urgent', 'deadline'],
    isAgenticTask: false,
    aiSuggested: false,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
];

// Helper functions
const formatDate = (date: Date): string => {
  return date.toISOString().split('T')[0];
};

const formatTime = (date: Date): string => {
  return date.toTimeString().slice(0, 5);
};

const parseLocalTime = (dateStr: string, timeStr: string): Date => {
  return new Date(`${dateStr}T${timeStr}:00`);
};

const getTimePosition = (time: string): number => {
  const date = new Date(time);
  const hours = date.getHours();
  const minutes = date.getMinutes();
  return (hours * 60 + minutes) / (24 * 60);
};

const getDuration = (startTime: string, endTime: string): number => {
  const start = new Date(startTime);
  const end = new Date(endTime);
  return (end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24);
};

const SchedulerKanban: React.FC<SchedulerKanbanProps> = ({ 
  apiBase = '' 
}) => {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [tasks, setTasks] = useState<SchedulerTask[]>(mockTasks);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<SchedulerTask | null>(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [draggedTask, setDraggedTask] = useState<SchedulerTask | null>(null);
  const timelineRef = useRef<HTMLDivElement>(null);

  type Priority = 'High' | 'Medium' | 'Low';
  // Form state for task editing
  const [formData, setFormData] = useState<{
    title: string;
    description: string;
    startTime: string;
    endTime: string;
    priority: Priority;
    isAgenticTask: boolean;
    tags: string;
  }>({
    title: '',
    description: '',
    startTime: '09:00',
    endTime: '10:00',
    priority: 'Medium',
    isAgenticTask: false,
    tags: '',
  });

  // Fetch tasks for the selected date (mock implementation)
  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      
      // Filter mock tasks for selected date
      const dateStr = formatDate(selectedDate);
      const filteredTasks = mockTasks.filter(task => task.date === dateStr);
      setTasks(filteredTasks);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  }, [selectedDate]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Navigation handlers
  const goToPreviousDay = () => {
    const prev = new Date(selectedDate);
    prev.setDate(prev.getDate() - 1);
    setSelectedDate(prev);
  };

  const goToNextDay = () => {
    const next = new Date(selectedDate);
    next.setDate(next.getDate() + 1);
    setSelectedDate(next);
  };

  const goToToday = () => {
    setSelectedDate(new Date());
  };

  // Task CRUD operations (mock implementations)
  const createTask = async () => {
    try {
      const dateStr = formatDate(selectedDate);
      const startAt = parseLocalTime(dateStr, formData.startTime).toISOString();
      const endAt = parseLocalTime(dateStr, formData.endTime).toISOString();
      
      const newTask: SchedulerTask = {
        id: `task-${Date.now()}`,
        title: formData.title,
        description: formData.description,
        startAt,
        endAt,
        date: dateStr,
        priority: formData.priority,
        status: 'pending',
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        isAgenticTask: formData.isAgenticTask,
        aiSuggested: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      setTasks(prev => [...prev, newTask]);
      resetForm();
    } catch (err) {
      console.error('Error creating task:', err);
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  const updateTask = async (taskId: string, updates: Partial<SchedulerTask>) => {
    try {
      setTasks(prev => prev.map(task => 
        task.id === taskId 
          ? { ...task, ...updates, updatedAt: new Date().toISOString() }
          : task
      ));
    } catch (err) {
      console.error('Error updating task:', err);
      setError(err instanceof Error ? err.message : 'Failed to update task');
    }
  };

  const deleteTask = async (taskId: string) => {
    try {
      setTasks(prev => prev.filter(task => task.id !== taskId));
    } catch (err) {
      console.error('Error deleting task:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  const markCompleted = async (taskId: string) => {
    await updateTask(taskId, { status: 'completed' });
  };

  const rescheduleTask = async (taskId: string) => {
    // Mock implementation - move task 1 hour forward
    const task = tasks.find(t => t.id === taskId);
    if (task) {
      const newStartAt = new Date(new Date(task.startAt).getTime() + 60 * 60 * 1000).toISOString();
      const newEndAt = new Date(new Date(task.endAt).getTime() + 60 * 60 * 1000).toISOString();
      await updateTask(taskId, { startAt: newStartAt, endAt: newEndAt });
    }
  };

  const notifyMissed = async (taskId: string) => {
    console.log(`Notification sent for missed task: ${taskId}`);
  };

  // Form handlers
  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      startTime: '09:00',
      endTime: '10:00',
      priority: 'Medium',
      isAgenticTask: false,
      tags: '',
    });
    setEditingTask(null);
    setIsCreateMode(false);
  };

  const openEditDialog = (task: SchedulerTask) => {
    const startTime = formatTime(new Date(task.startAt));
    const endTime = formatTime(new Date(task.endAt));
    
    setFormData({
      title: task.title,
      description: task.description || '',
      startTime,
      endTime,
      priority: task.priority,
      isAgenticTask: task.isAgenticTask || false,
      tags: task.tags?.join(', ') || '',
    });
    setEditingTask(task);
    setIsCreateMode(false);
  };

  const openCreateDialog = () => {
    resetForm();
    setIsCreateMode(true);
  };

  const handleSubmit = async () => {
    if (isCreateMode) {
      await createTask();
    } else if (editingTask) {
      const dateStr = formatDate(selectedDate);
      const startAt = parseLocalTime(dateStr, formData.startTime).toISOString();
      const endAt = parseLocalTime(dateStr, formData.endTime).toISOString();
      
      await updateTask(editingTask.id, {
        title: formData.title,
        description: formData.description,
        startAt,
        endAt,
        priority: formData.priority,
        isAgenticTask: formData.isAgenticTask,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
      });
      resetForm();
    }
  };

  // Drag and drop handlers
  const handleDragStart = (e: React.DragEvent, task: SchedulerTask) => {
    setDraggedTask(task);
    e.dataTransfer.effectAllowed = 'move';
  };

  const handleDragOver = (e: React.DragEvent) => {
    e.preventDefault();
    e.dataTransfer.dropEffect = 'move';
  };

  const handleDrop = (e: React.DragEvent, hourIndex: number) => {
    e.preventDefault();
    
    if (!draggedTask) return;
    
    const dateStr = formatDate(selectedDate);
    const startTime = `${hourIndex.toString().padStart(2, '0')}:00`;
    const startAt = parseLocalTime(dateStr, startTime).toISOString();
    
    // Calculate duration and set end time
    const originalDuration = new Date(draggedTask.endAt).getTime() - new Date(draggedTask.startAt).getTime();
    const endAt = new Date(new Date(startAt).getTime() + originalDuration).toISOString();
    
    updateTask(draggedTask.id, { startAt, endAt });
    setDraggedTask(null);
  };

  // Get tasks for the current day
  const currentDayTasks = tasks.filter(task => {
    const taskDate = new Date(task.startAt);
    const selectedDateStr = formatDate(selectedDate);
    const taskDateStr = formatDate(taskDate);
    return taskDateStr === selectedDateStr;
  });

  // Get missed tasks
  const now = new Date();
  const missedTasks = tasks.filter(task => 
    new Date(task.endAt) < now && task.status !== 'completed'
  );

  // Render timeline hours
  const hours = Array.from({ length: 24 }, (_, i) => i);

  // Priority configurations matching the theme
  const priorityConfig = {
    High: { color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' },
    Medium: { color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
    Low: { color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  };

  return (
    <div className="flex h-screen bg-gray-950 text-white">
      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <div className="bg-gray-900/50 border-b border-gray-800 p-4 backdrop-blur-sm">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-4">
              <button
                onClick={goToPreviousDay}
                className="p-2 hover:bg-gray-800 rounded-md transition-colors"
                aria-label="Previous day"
              >
                <ChevronLeft className="w-5 h-5" />
              </button>
              
              <button
                onClick={goToToday}
                className="px-3 py-1 text-sm bg-blue-600/20 text-blue-400 rounded-md hover:bg-blue-600/30 border border-blue-600/20 transition-colors"
              >
                Today
              </button>
              
              <button
                onClick={goToNextDay}
                className="p-2 hover:bg-gray-800 rounded-md transition-colors"
                aria-label="Next day"
              >
                <ChevronRight className="w-5 h-5" />
              </button>
            </div>
            
            <div className="text-center">
              <h1 className="text-2xl font-semibold text-white">
                {selectedDate.toLocaleDateString('en-US', { 
                  weekday: 'long', 
                  year: 'numeric', 
                  month: 'long', 
                  day: 'numeric' 
                })}
              </h1>
              <p className="text-sm text-gray-400">
                {formatDate(selectedDate)}
              </p>
            </div>
            
            <button
              onClick={openCreateDialog}
              className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 text-white rounded-md hover:from-blue-700 hover:to-purple-700 transition-all shadow-lg"
            >
              <Plus className="w-4 h-4" />
              <span>Add Task</span>
            </button>
          </div>
        </div>

        {/* Timeline */}
        <div className="flex-1 overflow-y-auto bg-gray-950">
          {loading ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-gray-400">Loading tasks...</div>
            </div>
          ) : error ? (
            <div className="flex items-center justify-center h-64">
              <div className="text-red-400">Error: {error}</div>
            </div>
          ) : (
            <div ref={timelineRef} className="relative">
              {hours.map((hour) => (
                <div
                  key={hour}
                  className="flex border-b border-gray-800/50 hover:bg-gray-900/30 transition-colors"
                  onDragOver={handleDragOver}
                  onDrop={(e) => handleDrop(e, hour)}
                >
                  {/* Time Label */}
                  <div className="w-20 flex-shrink-0 p-4 text-sm text-gray-500 border-r border-gray-800/50">
                    {hour.toString().padStart(2, '0')}:00
                  </div>
                  
                  {/* Hour Content */}
                  <div className="flex-1 relative min-h-[60px] p-2">
                    {/* Tasks for this hour */}
                    {currentDayTasks
                      .filter(task => {
                        const taskStart = new Date(task.startAt);
                        const taskHour = taskStart.getHours();
                        return taskHour === hour;
                      })
                      .map(task => {
                        const topPosition = getTimePosition(task.startAt) * 24 * 60 - (hour * 60);
                        const duration = getDuration(task.startAt, task.endAt);
                        const heightInMinutes = duration * 24 * 60;
                        const priority = priorityConfig[task.priority];
                        const isOverdue = new Date(task.endAt) < now;
                        
                        return (
                          <div
                            key={task.id}
                            draggable
                            onDragStart={(e) => handleDragStart(e, task)}
                            className={`absolute left-2 right-2 bg-gray-900/80 backdrop-blur-sm border rounded-xl shadow-lg p-3 cursor-move hover:shadow-xl transition-all group ${
                              priority.border
                            } ${task.status === 'completed' ? 'opacity-60' : ''}`}
                            style={{
                              top: `${Math.max(0, topPosition)}px`,
                              height: `${Math.max(40, heightInMinutes)}px`,
                              borderLeftWidth: '4px',
                            }}
                          >
                            <div className="flex items-start justify-between h-full">
                              <div className="flex-1 min-w-0">
                                <h3 className={`text-sm font-medium text-white truncate ${
                                  task.status === 'completed' ? 'line-through' : ''
                                }`}>
                                  {task.title}
                                </h3>
                                
                                {task.description && (
                                  <p className="text-xs text-gray-400 mt-1 line-clamp-2">
                                    {task.description}
                                  </p>
                                )}
                                
                                <div className="flex items-center gap-2 mt-2">
                                  <div className="flex items-center space-x-1 text-xs text-gray-400">
                                    <Clock className="w-3 h-3" />
                                    <span>
                                      {formatTime(new Date(task.startAt))} - {formatTime(new Date(task.endAt))}
                                    </span>
                                    {isOverdue && <AlertTriangle className="w-3 h-3 text-red-400" />}
                                  </div>
                                  
                                  {/* Priority Badge */}
                                  <div className={`inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium ${priority.bg} ${priority.color} ${priority.border} border`}>
                                    {task.priority}
                                  </div>
                                  
                                  {task.aiSuggested && (
                                    <div className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-purple-600/20 text-purple-400 border border-purple-600/20">
                                      AI
                                    </div>
                                  )}
                                  
                                  {task.isAgenticTask && (
                                    <div className="inline-flex items-center px-1.5 py-0.5 rounded text-xs font-medium bg-blue-600/20 text-blue-400 border border-blue-600/20">
                                      <Bot className="w-3 h-3 mr-1" />
                                      Agent
                                    </div>
                                  )}
                                </div>
                                
                                {/* Tags */}
                                {task.tags && task.tags.length > 0 && (
                                  <div className="flex flex-wrap gap-1 mt-1">
                                    {task.tags.slice(0, 2).map((tag) => (
                                      <div key={tag} className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-700/50 text-gray-300">
                                        {tag}
                                      </div>
                                    ))}
                                    {task.tags.length > 2 && (
                                      <div className="inline-flex items-center px-1.5 py-0.5 rounded text-xs bg-gray-700/50 text-gray-300">
                                        +{task.tags.length - 2}
                                      </div>
                                    )}
                                  </div>
                                )}
                              </div>
                              
                              {/* Task Actions */}
                              <div className="flex items-center space-x-1 opacity-0 group-hover:opacity-100 transition-opacity ml-2">
                                <button
                                  onClick={() => openEditDialog(task)}
                                  className="p-1 hover:bg-gray-700 rounded"
                                  title="Edit task"
                                >
                                  <Edit3 className="w-3 h-3 text-gray-400" />
                                </button>
                                
                                {task.status !== 'completed' && (
                                  <button
                                    onClick={() => markCompleted(task.id)}
                                    className="p-1 hover:bg-gray-700 rounded"
                                    title="Mark completed"
                                  >
                                    <CheckCircle2 className="w-3 h-3 text-green-500" />
                                  </button>
                                )}
                                
                                <button
                                  onClick={() => rescheduleTask(task.id)}
                                  className="p-1 hover:bg-gray-700 rounded"
                                  title="AI Reschedule"
                                >
                                  <AlertCircle className="w-3 h-3 text-blue-500" />
                                </button>
                                
                                {isOverdue && task.status !== 'completed' && (
                                  <button
                                    onClick={() => notifyMissed(task.id)}
                                    className="p-1 hover:bg-gray-700 rounded"
                                    title="Notify missed"
                                  >
                                    <Mail className="w-3 h-3 text-orange-500" />
                                  </button>
                                )}
                              </div>
                            </div>
                          </div>
                        );
                      })}
                  </div>
                </div>
              ))}
            </div>
          )}
        </div>
      </div>

      {/* Right Panel */}
      <div className="w-80 bg-gray-900/50 border-l border-gray-800 backdrop-blur-sm">
        <div className="p-4">
          {/* Quick Actions */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-white mb-3">Quick Actions</h3>
            <div className="space-y-2">
              <button
                onClick={fetchTasks}
                className="w-full flex items-center space-x-2 px-3 py-2 text-left hover:bg-gray-800/50 rounded-md transition-colors"
              >
                <AlertCircle className="w-4 h-4 text-blue-400" />
                <span className="text-gray-300">Refresh Tasks</span>
              </button>
              
              <button
                onClick={openCreateDialog}
                className="w-full flex items-center space-x-2 px-3 py-2 text-left hover:bg-gray-800/50 rounded-md transition-colors"
              >
                <Plus className="w-4 h-4 text-green-400" />
                <span className="text-gray-300">Add Task</span>
              </button>
            </div>
          </div>

          {/* Missed Tasks */}
          <div className="mb-6">
            <h3 className="text-lg font-medium text-white mb-3">
              Missed Tasks ({missedTasks.length})
            </h3>
            
            {missedTasks.length === 0 ? (
              <p className="text-sm text-gray-500">No missed tasks</p>
            ) : (
              <div className="space-y-2 max-h-64 overflow-y-auto">
                {missedTasks.map(task => (
                  <div
                    key={task.id}
                    className="p-3 bg-red-600/20 border border-red-600/30 rounded-md backdrop-blur-sm"
                  >
                    <div className="flex items-start justify-between">
                      <div className="flex-1 min-w-0">
                        <h4 className="text-sm font-medium text-red-300 truncate">
                          {task.title}
                        </h4>
                        <p className="text-xs text-red-400 mt-1">
                          Due: {formatTime(new Date(task.endAt))}
                        </p>
                      </div>
                      
                      <button
                        onClick={() => notifyMissed(task.id)}
                        className="p-1 hover:bg-red-600/30 rounded"
                        title="Send notification"
                      >
                        <Mail className="w-3 h-3 text-red-400" />
                      </button>
                    </div>
                  </div>
                ))}
              </div>
            )}
          </div>

          {/* AI Suggestions */}
          <div>
            <h3 className="text-lg font-medium text-white mb-3">AI Suggestions</h3>
            <div className="p-3 bg-purple-600/20 border border-purple-600/30 rounded-md backdrop-blur-sm">
              <p className="text-sm text-purple-300">
                Try drag & drop to quickly reschedule tasks, or use the AI reschedule feature for intelligent suggestions.
              </p>
            </div>
          </div>
        </div>
      </div>

      {/* Edit/Create Task Dialog */}
      {(editingTask || isCreateMode) && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50">
          <div className="bg-gray-900 border border-gray-700 rounded-xl shadow-2xl w-full max-w-md mx-4">
            <div className="p-6">
              <h2 className="text-lg font-medium text-white mb-4">
                {isCreateMode ? 'Create Task' : 'Edit Task'}
              </h2>
              
              <div className="space-y-4">
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Title
                  </label>
                  <input
                    type="text"
                    value={formData.title}
                    onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    placeholder="Task title"
                  />
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Description
                  </label>
                  <textarea
                    value={formData.description}
                    onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    rows={3}
                    placeholder="Task description (optional)"
                  />
                </div>
                
                <div className="grid grid-cols-2 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      Start Time
                    </label>
                    <input
                      type="time"
                      value={formData.startTime}
                      onChange={(e) => setFormData(prev => ({ ...prev, startTime: e.target.value }))}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    />
                  </div>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">
                      End Time
                    </label>
                    <input
                      type="time"
                      value={formData.endTime}
                      onChange={(e) => setFormData(prev => ({ ...prev, endTime: e.target.value }))}
                      className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    />
                  </div>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Priority
                  </label>
                  <select
                    value={formData.priority}
                    onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as 'High' | 'Medium' | 'Low' }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                  >
                    <option value="High">High Priority</option>
                    <option value="Medium">Medium Priority</option>
                    <option value="Low">Low Priority</option>
                  </select>
                </div>
                
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-1">
                    Tags (comma-separated)
                  </label>
                  <input
                    type="text"
                    value={formData.tags}
                    onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                    className="w-full px-3 py-2 bg-gray-800 border border-gray-600 rounded-md focus:outline-none focus:ring-2 focus:ring-blue-500 text-white"
                    placeholder="project, urgent, personal..."
                  />
                </div>
                
                <div className="flex items-center space-x-2">
                  <input
                    type="checkbox"
                    id="agentic"
                    checked={formData.isAgenticTask}
                    onChange={(e) => setFormData(prev => ({ ...prev, isAgenticTask: e.target.checked }))}
                    className="rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500 focus:ring-2"
                  />
                  <label htmlFor="agentic" className="text-sm text-gray-300">
                    Make this an Agentic Task
                  </label>
                </div>
              </div>
              
              <div className="flex justify-end space-x-3 mt-6">
                <button
                  onClick={resetForm}
                  className="px-4 py-2 text-sm font-medium text-gray-300 bg-gray-700 hover:bg-gray-600 rounded-md transition-colors"
                >
                  Cancel
                </button>
                
                {!isCreateMode && editingTask && (
                  <button
                    onClick={() => {
                      deleteTask(editingTask.id);
                      resetForm();
                    }}
                    className="px-4 py-2 text-sm font-medium text-white bg-red-600 hover:bg-red-700 rounded-md transition-colors"
                  >
                    Delete
                  </button>
                )}
                
                <button
                  onClick={handleSubmit}
                  className="px-4 py-2 text-sm font-medium text-white bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 rounded-md transition-all"
                  disabled={!formData.title.trim()}
                >
                  {isCreateMode ? 'Create' : 'Save'}
                </button>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  );
};

export default SchedulerKanban;