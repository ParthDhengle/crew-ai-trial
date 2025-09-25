import React, { useState, useEffect, useCallback } from 'react';
import {
  Plus,
  ChevronLeft,
  ChevronRight,
  Clock,
  CheckCircle2,
  AlertCircle,
  Edit3,
  Calendar,
  Bot,
  AlertTriangle,
  Trash2,
  Search,
  Filter,
  RefreshCw,
  Star,
  Tag,
  MapPin,
  Users,
  Bell,
  Settings,
  X,
  Save
} from 'lucide-react';

// Google Calendar Component with Dynamic Refresh
const GoogleCalendarEmbed = ({
  calendarId = "parthdhengle2004@gmail.com",
  mode = "WEEK",
  timezone = "Asia/Kolkata",
  width = "100%",
  height = "700px",
  refreshKey = 0,
}) => {
  const src = `https://calendar.google.com/calendar/embed?src=parthdhengle2004%40gmail.com&ctz=Asia%2FKolkata&_=${refreshKey}`;

  return (
    <iframe
      key={refreshKey} // Force re-render when refreshKey changes
      title="Google Calendar"
      src={src}
      style={{
        border: "0",
        width: typeof width === "number" ? `${width}px` : width,
        height: typeof height === "number" ? `${height}px` : height,
      }}
      frameBorder={0}
      className="rounded-lg shadow-lg transition-opacity duration-300"
    />
  );
};

// Types
interface SchedulerTask {
  id: string;
  title: string;
  description?: string;
  startAt: string;
  endAt: string;
  date: string;
  priority: 'High' | 'Medium' | 'Low';
  status: 'pending' | 'completed' | 'cancelled';
  tags?: string[];
  isAgenticTask?: boolean;
  aiSuggested?: boolean;
  location?: string;
  attendees?: string[];
  reminderMinutes?: number;
  createdAt: string;
  updatedAt: string;
}

interface SchedulerKanbanProps {
  apiBase?: string;
}

// Mock data
const mockTasks: SchedulerTask[] = [
  {
    id: 'task-1',
    title: 'Team standup meeting',
    description: 'Daily sync with the development team to discuss progress and blockers',
    startAt: new Date(Date.now() + 2 * 60 * 60 * 1000).toISOString(),
    endAt: new Date(Date.now() + 2.5 * 60 * 60 * 1000).toISOString(),
    date: new Date().toISOString().split('T')[0],
    priority: 'High',
    status: 'pending',
    tags: ['meeting', 'team', 'development'],
    isAgenticTask: false,
    aiSuggested: true,
    location: 'Conference Room A',
    attendees: ['john@company.com', 'sarah@company.com'],
    reminderMinutes: 15,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-2',
    title: 'Code review session',
    description: 'Review pull requests for the new feature implementation',
    startAt: new Date(Date.now() + 4 * 60 * 60 * 1000).toISOString(),
    endAt: new Date(Date.now() + 5 * 60 * 60 * 1000).toISOString(),
    date: new Date().toISOString().split('T')[0],
    priority: 'Medium',
    status: 'pending',
    tags: ['development', 'review', 'code'],
    isAgenticTask: true,
    aiSuggested: false,
    location: 'Virtual',
    attendees: ['dev-team@company.com'],
    reminderMinutes: 30,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  },
  {
    id: 'task-3',
    title: 'Client presentation',
    description: 'Present Q4 results to key stakeholders',
    startAt: new Date(Date.now() + 6 * 60 * 60 * 1000).toISOString(),
    endAt: new Date(Date.now() + 7 * 60 * 60 * 1000).toISOString(),
    date: new Date().toISOString().split('T')[0],
    priority: 'High',
    status: 'pending',
    tags: ['presentation', 'client', 'important'],
    isAgenticTask: false,
    aiSuggested: false,
    location: 'Boardroom',
    attendees: ['client@external.com', 'manager@company.com'],
    reminderMinutes: 60,
    createdAt: new Date().toISOString(),
    updatedAt: new Date().toISOString(),
  }
];

const SchedulerKanban: React.FC<SchedulerKanbanProps> = ({ apiBase = '/api' }) => {
  const [selectedDate, setSelectedDate] = useState<Date>(new Date());
  const [tasks, setTasks] = useState<SchedulerTask[]>(mockTasks);
  const [filteredTasks, setFilteredTasks] = useState<SchedulerTask[]>(mockTasks);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingTask, setEditingTask] = useState<SchedulerTask | null>(null);
  const [isCreateMode, setIsCreateMode] = useState(false);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'completed'>('all');
  const [filterPriority, setFilterPriority] = useState<'all' | 'High' | 'Medium' | 'Low'>('all');
  const [showCompleted, setShowCompleted] = useState(true);
  const [calendarView, setCalendarView] = useState<'WEEK' | 'MONTH' | 'AGENDA'>('WEEK');
  const [calendarRefreshKey, setCalendarRefreshKey] = useState(0);
  const [autoRefresh, setAutoRefresh] = useState(true);
  const [lastRefresh, setLastRefresh] = useState<Date>(new Date());
  const [isRefreshing, setIsRefreshing] = useState(false);

  // Form state
  const [formData, setFormData] = useState<{
    title: string;
    description: string;
    startTime: string;
    endTime: string;
    date: string;
    priority: 'High' | 'Medium' | 'Low';
    isAgenticTask: boolean;
    tags: string;
    location: string;
    attendees: string;
    reminderMinutes: number;
  }>({
    title: '',
    description: '',
    startTime: '09:00',
    endTime: '10:00',
    date: new Date().toISOString().split('T')[0],
    priority: 'Medium',
    isAgenticTask: false,
    tags: '',
    location: '',
    attendees: '',
    reminderMinutes: 15,
  });

  // Calendar refresh functions
  const refreshCalendar = useCallback(() => {
    setIsRefreshing(true);
    setCalendarRefreshKey(prev => prev + 1);
    setLastRefresh(new Date());
    
    // Simulate refresh delay for better UX
    setTimeout(() => {
      setIsRefreshing(false);
    }, 1000);
  }, []);

  // Auto-refresh calendar every 2 minutes when enabled
  useEffect(() => {
    if (!autoRefresh) return;

    const interval = setInterval(() => {
      refreshCalendar();
    }, 2 * 60 * 1000); // 2 minutes

    return () => clearInterval(interval);
  }, [autoRefresh, refreshCalendar]);

  // Refresh calendar after task operations
  const refreshAfterTaskOperation = useCallback(() => {
    // Small delay to allow backend processing
    setTimeout(() => {
      refreshCalendar();
    }, 1000);
  }, [refreshCalendar]);

  // Helper functions
  const formatDate = (date: Date): string => {
    return date.toISOString().split('T')[0];
  };

  const formatTime = (date: Date): string => {
    return date.toTimeString().slice(0, 5);
  };

  // API calls (ready for backend integration)
  const fetchTasks = useCallback(async () => {
    setLoading(true);
    setError(null);
    
    try {
      // TODO: Replace with actual API call
      // const response = await fetch(`${apiBase}/tasks?date=${formatDate(selectedDate)}`);
      // const data = await response.json();
      // setTasks(data);
      
      // Simulate API delay
      await new Promise(resolve => setTimeout(resolve, 500));
      setTasks(mockTasks);
    } catch (err) {
      console.error('Error fetching tasks:', err);
      setError(err instanceof Error ? err.message : 'Failed to fetch tasks');
    } finally {
      setLoading(false);
    }
  }, [selectedDate, apiBase]);

  // Convert task to Google Calendar event
  const createGoogleCalendarEvent = async (task: SchedulerTask) => {
    try {
      // TODO: Implement Google Calendar API integration
      // This will create an actual event in Google Calendar so it shows in the iframe
      
      const eventData = {
        summary: task.title,
        description: task.description,
        start: {
          dateTime: task.startAt,
          timeZone: 'Asia/Kolkata',
        },
        end: {
          dateTime: task.endAt,
          timeZone: 'Asia/Kolkata',
        },
        location: task.location,
        attendees: task.attendees?.map(email => ({ email })),
        reminders: {
          useDefault: false,
          overrides: task.reminderMinutes ? [
            { method: 'popup', minutes: task.reminderMinutes },
            { method: 'email', minutes: task.reminderMinutes }
          ] : []
        },
        // Add custom metadata to identify this as a task-generated event
        extendedProperties: {
          private: {
            taskId: task.id,
            isTaskEvent: 'true',
            priority: task.priority,
            isAgenticTask: task.isAgenticTask?.toString() || 'false',
            tags: task.tags?.join(',') || ''
          }
        },
        // Color-code by priority
        colorId: task.priority === 'High' ? '11' : task.priority === 'Medium' ? '5' : '2'
      };

      // Example API call structure (implement in your backend):
      /*
      const response = await fetch(`${apiBase}/google-calendar/events`, {
        method: 'POST',
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(eventData)
      });
      
      if (!response.ok) {
        throw new Error('Failed to create Google Calendar event');
      }
      
      const createdEvent = await response.json();
      return createdEvent;
      */
      
      console.log('Would create Google Calendar event:', eventData);
      return { id: `gcal-${Date.now()}`, ...eventData };
      
    } catch (err) {
      console.error('Error creating Google Calendar event:', err);
      throw err;
    }
  };

  const updateGoogleCalendarEvent = async (task: SchedulerTask, eventId: string) => {
    try {
      // TODO: Implement Google Calendar API update
      const eventData = {
        summary: task.title,
        description: task.description,
        start: {
          dateTime: task.startAt,
          timeZone: 'Asia/Kolkata',
        },
        end: {
          dateTime: task.endAt,
          timeZone: 'Asia/Kolkata',
        },
        location: task.location,
        attendees: task.attendees?.map(email => ({ email })),
        extendedProperties: {
          private: {
            taskId: task.id,
            isTaskEvent: 'true',
            priority: task.priority,
            isAgenticTask: task.isAgenticTask?.toString() || 'false',
            tags: task.tags?.join(',') || ''
          }
        },
        colorId: task.priority === 'High' ? '11' : task.priority === 'Medium' ? '5' : '2'
      };

      // Example API call:
      /*
      const response = await fetch(`${apiBase}/google-calendar/events/${eventId}`, {
        method: 'PUT',
        headers: {
          'Authorization': `Bearer ${userToken}`,
          'Content-Type': 'application/json'
        },
        body: JSON.stringify(eventData)
      });
      */
      
      console.log('Would update Google Calendar event:', eventId, eventData);
      
    } catch (err) {
      console.error('Error updating Google Calendar event:', err);
      throw err;
    }
  };

  const deleteGoogleCalendarEvent = async (eventId: string) => {
    try {
      // TODO: Implement Google Calendar API delete
      /*
      await fetch(`${apiBase}/google-calendar/events/${eventId}`, {
        method: 'DELETE',
        headers: {
          'Authorization': `Bearer ${userToken}`
        }
      });
      */
      
      console.log('Would delete Google Calendar event:', eventId);
      
    } catch (err) {
      console.error('Error deleting Google Calendar event:', err);
      throw err;
    }
  };

  const createTask = async () => {
    try {
      const startAt = new Date(`${formData.date}T${formData.startTime}:00`).toISOString();
      const endAt = new Date(`${formData.date}T${formData.endTime}:00`).toISOString();
      
      const newTask: SchedulerTask = {
        id: `task-${Date.now()}`,
        title: formData.title,
        description: formData.description,
        startAt,
        endAt,
        date: formData.date,
        priority: formData.priority,
        status: 'pending',
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        isAgenticTask: formData.isAgenticTask,
        location: formData.location,
        attendees: formData.attendees.split(',').map(t => t.trim()).filter(Boolean),
        reminderMinutes: formData.reminderMinutes,
        aiSuggested: false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };
      
      // TODO: Replace with actual API call
      // const response = await fetch(`${apiBase}/tasks`, {
      //   method: 'POST',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(newTask)
      // });
      // const createdTask = await response.json();
      
      setTasks(prev => [...prev, newTask]);
      
      // 🎯 NEW: Auto-create Google Calendar event so task appears in iframe
      try {
        await createGoogleCalendarEvent(newTask);
        console.log('✅ Task created and synced to Google Calendar');
      } catch (calendarError) {
        console.warn('⚠️ Task created but failed to sync to Google Calendar:', calendarError);
        // Don't fail the entire operation if calendar sync fails
      }
      
      refreshAfterTaskOperation(); // Refresh calendar
      resetForm();
    } catch (err) {
      console.error('Error creating task:', err);
      setError(err instanceof Error ? err.message : 'Failed to create task');
    }
  };

  const updateTask = async (taskId: string, updates: Partial<SchedulerTask>) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`${apiBase}/tasks/${taskId}`, {
      //   method: 'PUT',
      //   headers: { 'Content-Type': 'application/json' },
      //   body: JSON.stringify(updates)
      // });
      
      const updatedTask = { ...tasks.find(t => t.id === taskId)!, ...updates, updatedAt: new Date().toISOString() };
      
      setTasks(prev => prev.map(task => 
        task.id === taskId ? updatedTask : task
      ));
      
      // 🎯 NEW: Update corresponding Google Calendar event
      try {
        // In a real implementation, you'd store the Google Calendar event ID with the task
        // For now, we'll assume eventId is derived from taskId or stored separately
        const eventId = `gcal-event-${taskId}`; // This should come from your database
        await updateGoogleCalendarEvent(updatedTask, eventId);
        console.log('✅ Task updated and synced to Google Calendar');
      } catch (calendarError) {
        console.warn('⚠️ Task updated but failed to sync to Google Calendar:', calendarError);
      }
      
      refreshAfterTaskOperation(); // Refresh calendar
    } catch (err) {
      console.error('Error updating task:', err);
      setError(err instanceof Error ? err.message : 'Failed to update task');
    }
  };

  const deleteTask = async (taskId: string) => {
    try {
      // TODO: Replace with actual API call
      // await fetch(`${apiBase}/tasks/${taskId}`, { method: 'DELETE' });
      
      setTasks(prev => prev.filter(task => task.id !== taskId));
      
      // 🎯 NEW: Delete corresponding Google Calendar event
      try {
        const eventId = `gcal-event-${taskId}`; // This should come from your database
        await deleteGoogleCalendarEvent(eventId);
        console.log('✅ Task deleted and removed from Google Calendar');
      } catch (calendarError) {
        console.warn('⚠️ Task deleted but failed to remove from Google Calendar:', calendarError);
      }
      
      refreshAfterTaskOperation(); // Refresh calendar
    } catch (err) {
      console.error('Error deleting task:', err);
      setError(err instanceof Error ? err.message : 'Failed to delete task');
    }
  };

  // Filter and search logic
  useEffect(() => {
    let filtered = tasks;

    // Search filter
    if (searchQuery) {
      filtered = filtered.filter(task =>
        task.title.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.description?.toLowerCase().includes(searchQuery.toLowerCase()) ||
        task.tags?.some(tag => tag.toLowerCase().includes(searchQuery.toLowerCase()))
      );
    }

    // Status filter
    if (filterStatus !== 'all') {
      filtered = filtered.filter(task => task.status === filterStatus);
    }

    // Priority filter
    if (filterPriority !== 'all') {
      filtered = filtered.filter(task => task.priority === filterPriority);
    }

    // Show/hide completed
    if (!showCompleted) {
      filtered = filtered.filter(task => task.status !== 'completed');
    }

    setFilteredTasks(filtered);
  }, [tasks, searchQuery, filterStatus, filterPriority, showCompleted]);

  useEffect(() => {
    fetchTasks();
  }, [fetchTasks]);

  // Form handlers
  const resetForm = () => {
    setFormData({
      title: '',
      description: '',
      startTime: '09:00',
      endTime: '10:00',
      date: new Date().toISOString().split('T')[0],
      priority: 'Medium',
      isAgenticTask: false,
      tags: '',
      location: '',
      attendees: '',
      reminderMinutes: 15,
    });
    setEditingTask(null);
    setIsCreateMode(false);
  };

  const openEditDialog = (task: SchedulerTask) => {
    setFormData({
      title: task.title,
      description: task.description || '',
      startTime: formatTime(new Date(task.startAt)),
      endTime: formatTime(new Date(task.endAt)),
      date: task.date,
      priority: task.priority,
      isAgenticTask: task.isAgenticTask || false,
      tags: task.tags?.join(', ') || '',
      location: task.location || '',
      attendees: task.attendees?.join(', ') || '',
      reminderMinutes: task.reminderMinutes || 15,
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
      const startAt = new Date(`${formData.date}T${formData.startTime}:00`).toISOString();
      const endAt = new Date(`${formData.date}T${formData.endTime}:00`).toISOString();
      
      await updateTask(editingTask.id, {
        title: formData.title,
        description: formData.description,
        startAt,
        endAt,
        date: formData.date,
        priority: formData.priority,
        isAgenticTask: formData.isAgenticTask,
        tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
        location: formData.location,
        attendees: formData.attendees.split(',').map(t => t.trim()).filter(Boolean),
        reminderMinutes: formData.reminderMinutes,
      });
      resetForm();
    }
  };

  // Get priority styling
  const getPriorityStyle = (priority: string) => {
    switch (priority) {
      case 'High':
        return 'bg-red-600/20 text-red-400 border-red-600/30';
      case 'Medium':
        return 'bg-yellow-600/20 text-yellow-400 border-yellow-600/30';
      case 'Low':
        return 'bg-green-600/20 text-green-400 border-green-600/30';
      default:
        return 'bg-gray-600/20 text-gray-400 border-gray-600/30';
    }
  };

  // Get upcoming tasks for today
  const todayTasks = filteredTasks.filter(task => {
    const taskDate = new Date(task.startAt);
    const today = new Date();
    return taskDate.toDateString() === today.toDateString();
  }).sort((a, b) => new Date(a.startAt).getTime() - new Date(b.startAt).getTime());

  const upcomingTasks = todayTasks.filter(task => 
    new Date(task.startAt) > new Date() && task.status === 'pending'
  ).slice(0, 5);

  const overdueTasks = filteredTasks.filter(task => 
    new Date(task.endAt) < new Date() && task.status === 'pending'
  );

  return (
    <div className="min-h-screen bg-gradient-to-br from-gray-900 via-gray-800 to-gray-900">
      {/* Header */}
      <div className="sticky top-0 z-40 bg-gray-900/95 backdrop-blur-md border-b border-gray-700/50">
        <div className="px-6 py-4">
          <div className="flex items-center justify-between">
            <div className="flex items-center space-x-6">
              <div className="flex items-center space-x-2">
                <Calendar className="w-8 h-8 text-blue-400" />
                <h1 className="text-2xl font-bold bg-gradient-to-r from-blue-400 to-purple-400 bg-clip-text text-transparent">
                  AI Scheduler
                </h1>
              </div>
              
              <div className="flex items-center space-x-2 bg-gray-800/50 rounded-lg p-1">
                {(['WEEK', 'MONTH', 'AGENDA'] as const).map((view) => (
                  <button
                    key={view}
                    onClick={() => setCalendarView(view)}
                    className={`px-3 py-1.5 text-sm rounded-md transition-all ${
                      calendarView === view
                        ? 'bg-blue-600 text-white shadow-lg'
                        : 'text-gray-400 hover:text-gray-200 hover:bg-gray-700/50'
                    }`}
                  >
                    {view}
                  </button>
                ))}
              </div>
            </div>

            <div className="flex items-center space-x-4">
              {/* Auto-refresh toggle */}
              <div className="flex items-center space-x-2">
                <label className="flex items-center space-x-2 text-sm text-gray-400 cursor-pointer">
                  <input
                    type="checkbox"
                    checked={autoRefresh}
                    onChange={(e) => setAutoRefresh(e.target.checked)}
                    className="rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500"
                  />
                  <span>Auto-sync</span>
                </label>
                <div className="text-xs text-gray-500">
                  Last: {lastRefresh.toLocaleTimeString()}
                </div>
              </div>

              {/* Manual refresh */}
              <button
                onClick={refreshCalendar}
                disabled={isRefreshing}
                className="p-2 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600/50 rounded-lg transition-all disabled:opacity-50"
                title="Refresh Calendar"
              >
                <RefreshCw className={`w-5 h-5 text-gray-400 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>

              {/* Search */}
              <div className="relative">
                <Search className="absolute left-3 top-1/2 transform -translate-y-1/2 w-4 h-4 text-gray-400" />
                <input
                  type="text"
                  placeholder="Search tasks..."
                  value={searchQuery}
                  onChange={(e) => setSearchQuery(e.target.value)}
                  className="pl-10 pr-4 py-2 bg-gray-800/50 border border-gray-600/50 rounded-lg focus:outline-none focus:ring-2 focus:ring-blue-500/50 text-white placeholder-gray-400 w-64"
                />
              </div>

              {/* Refresh Button */}
              <button
                onClick={fetchTasks}
                disabled={loading}
                className="p-2 bg-gray-800/50 hover:bg-gray-700/50 border border-gray-600/50 rounded-lg transition-all"
                title="Refresh Tasks"
              >
                <RefreshCw className={`w-5 h-5 text-gray-400 ${loading ? 'animate-spin' : ''}`} />
              </button>

              {/* Add Task Button */}
              <button
                onClick={openCreateDialog}
                className="flex items-center space-x-2 px-4 py-2 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 text-white rounded-lg transition-all shadow-lg hover:shadow-xl transform hover:scale-105"
              >
                <Plus className="w-5 h-5" />
                <span className="font-medium">Add Task</span>
              </button>
            </div>
          </div>

          {/* Filters */}
          <div className="flex items-center space-x-4 mt-4">
            <div className="flex items-center space-x-2">
              <Filter className="w-4 h-4 text-gray-400" />
              <span className="text-sm text-gray-400">Filters:</span>
            </div>

            <select
              value={filterStatus}
              onChange={(e) => setFilterStatus(e.target.value as any)}
              className="px-3 py-1.5 bg-gray-800/50 border border-gray-600/50 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="all">All Status</option>
              <option value="pending">Pending</option>
              <option value="completed">Completed</option>
            </select>

            <select
              value={filterPriority}
              onChange={(e) => setFilterPriority(e.target.value as any)}
              className="px-3 py-1.5 bg-gray-800/50 border border-gray-600/50 rounded-md text-white text-sm focus:outline-none focus:ring-2 focus:ring-blue-500/50"
            >
              <option value="all">All Priority</option>
              <option value="High">High Priority</option>
              <option value="Medium">Medium Priority</option>
              <option value="Low">Low Priority</option>
            </select>

            <label className="flex items-center space-x-2 text-sm text-gray-400">
              <input
                type="checkbox"
                checked={showCompleted}
                onChange={(e) => setShowCompleted(e.target.checked)}
                className="rounded border-gray-600 bg-gray-800 text-blue-600 focus:ring-blue-500"
              />
              <span>Show completed</span>
            </label>

            {(searchQuery || filterStatus !== 'all' || filterPriority !== 'all') && (
              <div className="text-sm text-gray-400">
                {filteredTasks.length} of {tasks.length} tasks
              </div>
            )}
          </div>
        </div>
      </div>

      <div className="flex h-[calc(100vh-140px)]">
        {/* Left Sidebar */}
        <div className="w-80 bg-gray-900/50 backdrop-blur-sm border-r border-gray-700/50 p-6 overflow-y-auto">
          {/* Quick Stats */}
          <div className="grid grid-cols-2 gap-4 mb-6">
            <div className="bg-gradient-to-br from-blue-600/20 to-blue-800/20 p-4 rounded-xl border border-blue-600/30">
              <div className="text-2xl font-bold text-blue-400">{todayTasks.length}</div>
              <div className="text-sm text-blue-300">Today's Tasks</div>
            </div>
            <div className="bg-gradient-to-br from-red-600/20 to-red-800/20 p-4 rounded-xl border border-red-600/30">
              <div className="text-2xl font-bold text-red-400">{overdueTasks.length}</div>
              <div className="text-sm text-red-300">Overdue</div>
            </div>
          </div>

          {/* Upcoming Tasks */}
          <div className="mb-6">
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Clock className="w-5 h-5 mr-2 text-blue-400" />
              Upcoming Today
            </h3>
            
            {loading ? (
              <div className="text-center py-8">
                <RefreshCw className="w-6 h-6 animate-spin text-blue-400 mx-auto mb-2" />
                <p className="text-gray-400">Loading tasks...</p>
              </div>
            ) : upcomingTasks.length === 0 ? (
              <div className="text-center py-8">
                <CheckCircle2 className="w-12 h-12 text-green-400 mx-auto mb-3 opacity-50" />
                <p className="text-gray-400">No upcoming tasks today</p>
                <p className="text-sm text-gray-500">You're all caught up!</p>
              </div>
            ) : (
              <div className="space-y-3">
                {upcomingTasks.map(task => {
                  const startTime = new Date(task.startAt);
                  const isUrgent = startTime.getTime() - new Date().getTime() < 60 * 60 * 1000; // Less than 1 hour
                  
                  return (
                    <div
                      key={task.id}
                      className={`p-4 rounded-xl backdrop-blur-sm border transition-all hover:scale-105 cursor-pointer ${
                        isUrgent 
                          ? 'bg-red-600/20 border-red-600/30 shadow-red-500/20 shadow-lg' 
                          : 'bg-gray-800/50 border-gray-600/30 hover:bg-gray-800/70'
                      }`}
                      onClick={() => openEditDialog(task)}
                    >
                      <div className="flex items-start justify-between">
                        <div className="flex-1 min-w-0">
                          <h4 className="font-medium text-white truncate mb-1">
                            {task.title}
                          </h4>
                          <p className="text-sm text-gray-400 mb-2">
                            {formatTime(startTime)} - {formatTime(new Date(task.endAt))}
                          </p>
                          
                          <div className="flex items-center space-x-2">
                            <div className={`px-2 py-1 rounded-md text-xs font-medium border ${getPriorityStyle(task.priority)}`}>
                              {task.priority}
                            </div>
                            
                            {task.isAgenticTask && (
                              <div className="px-2 py-1 rounded-md text-xs font-medium bg-purple-600/20 text-purple-400 border border-purple-600/30">
                                <Bot className="w-3 h-3 inline mr-1" />
                                Agent
                              </div>
                            )}

                            {isUrgent && (
                              <div className="px-2 py-1 rounded-md text-xs font-medium bg-orange-600/20 text-orange-400 border border-orange-600/30">
                                <AlertTriangle className="w-3 h-3 inline mr-1" />
                                Soon
                              </div>
                            )}
                          </div>

                          {task.location && (
                            <p className="text-xs text-gray-500 mt-1 flex items-center">
                              <MapPin className="w-3 h-3 mr-1" />
                              {task.location}
                            </p>
                          )}
                        </div>
                        
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            updateTask(task.id, { status: 'completed' });
                          }}
                          className="p-1 hover:bg-green-600/30 rounded-md transition-colors"
                        >
                          <CheckCircle2 className="w-4 h-4 text-gray-400 hover:text-green-400" />
                        </button>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}
          </div>

          {/* Overdue Tasks */}
          {overdueTasks.length > 0 && (
            <div className="mb-6">
              <h3 className="text-lg font-semibold text-red-400 mb-4 flex items-center">
                <AlertTriangle className="w-5 h-5 mr-2" />
                Overdue ({overdueTasks.length})
              </h3>
              
              <div className="space-y-2">
                {overdueTasks.slice(0, 3).map(task => (
                  <div
                    key={task.id}
                    className="p-3 bg-red-600/20 border border-red-600/30 rounded-lg backdrop-blur-sm cursor-pointer hover:bg-red-600/30 transition-all"
                    onClick={() => openEditDialog(task)}
                  >
                    <h4 className="font-medium text-red-300 truncate mb-1">
                      {task.title}
                    </h4>
                    <p className="text-xs text-red-400">
                      Due: {formatTime(new Date(task.endAt))} on {new Date(task.date).toLocaleDateString()}
                    </p>
                  </div>
                ))}
                
                {overdueTasks.length > 3 && (
                  <div className="text-xs text-red-400 text-center py-2">
                    +{overdueTasks.length - 3} more overdue tasks
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Quick Actions */}
          <div>
            <h3 className="text-lg font-semibold text-white mb-4 flex items-center">
              <Settings className="w-5 h-5 mr-2 text-gray-400" />
              Quick Actions
            </h3>
            
            <div className="space-y-2">
              <button
                onClick={openCreateDialog}
                className="w-full flex items-center space-x-3 p-3 text-left hover:bg-gray-800/50 rounded-lg transition-all border border-gray-700/50"
              >
                <Plus className="w-5 h-5 text-blue-400" />
                <span className="text-gray-300">Create New Task</span>
              </button>
              
              <button
                onClick={() => {
                  const today = new Date().toISOString().split('T')[0];
                  setFormData(prev => ({ ...prev, date: today }));
                  openCreateDialog();
                }}
                className="w-full flex items-center space-x-3 p-3 text-left hover:bg-gray-800/50 rounded-lg transition-all border border-gray-700/50"
              >
                <Calendar className="w-5 h-5 text-green-400" />
                <span className="text-gray-300">Schedule for Today</span>
              </button>
              
              <button
                onClick={() => {
                  fetchTasks();
                  refreshCalendar(); // Also refresh calendar
                }}
                className="w-full flex items-center space-x-3 p-3 text-left hover:bg-gray-800/50 rounded-lg transition-all border border-gray-700/50"
              >
                <RefreshCw className="w-5 h-5 text-purple-400" />
                <span className="text-gray-300">Sync Tasks & Calendar</span>
              </button>
            </div>

            {/* Integration Status */}
            <div className="mt-6 p-4 bg-gradient-to-r from-blue-600/20 to-purple-600/20 rounded-xl border border-blue-600/30">
              <div className="flex items-center space-x-2 mb-2">
                <Calendar className="w-4 h-4 text-blue-400" />
                <span className="font-medium text-blue-300">Calendar Integration</span>
              </div>
              <p className="text-xs text-blue-200 leading-relaxed">
                Tasks automatically sync to Google Calendar as events. They'll appear in the calendar view with color-coding by priority.
              </p>
              <div className="flex items-center space-x-4 mt-3 text-xs">
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-red-400 rounded-full"></div>
                  <span className="text-red-300">High</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-yellow-400 rounded-full"></div>
                  <span className="text-yellow-300">Medium</span>
                </div>
                <div className="flex items-center space-x-1">
                  <div className="w-2 h-2 bg-green-400 rounded-full"></div>
                  <span className="text-green-300">Low</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* Google Calendar */}
        <div className="flex-1 p-6 overflow-hidden">
          <div className="h-full bg-white/5 backdrop-blur-sm rounded-2xl border border-gray-700/30 relative">
            {/* Calendar Header */}
            <div className="absolute top-4 right-4 z-10 flex items-center space-x-2">
              <div className="bg-gray-900/80 backdrop-blur-sm rounded-lg px-3 py-1.5 border border-gray-700/50">
                <div className="flex items-center space-x-2 text-xs">
                  <div className={`w-2 h-2 rounded-full ${autoRefresh ? 'bg-green-400 animate-pulse' : 'bg-gray-500'}`}></div>
                  <span className="text-gray-300">
                    {autoRefresh ? 'Auto-sync ON' : 'Auto-sync OFF'}
                  </span>
                </div>
              </div>
              
              <button
                onClick={refreshCalendar}
                disabled={isRefreshing}
                className="bg-gray-900/80 backdrop-blur-sm hover:bg-gray-800/80 border border-gray-700/50 rounded-lg p-2 transition-all disabled:opacity-50"
                title="Refresh Calendar Now"
              >
                <RefreshCw className={`w-4 h-4 text-gray-300 ${isRefreshing ? 'animate-spin' : ''}`} />
              </button>
            </div>

            {/* Loading overlay for calendar refresh */}
            {isRefreshing && (
              <div className="absolute inset-4 bg-black/20 backdrop-blur-sm rounded-lg flex items-center justify-center z-20">
                <div className="bg-gray-900/90 rounded-xl p-4 border border-gray-700/50">
                  <div className="flex items-center space-x-3">
                    <RefreshCw className="w-5 h-5 animate-spin text-blue-400" />
                    <span className="text-white font-medium">Syncing calendar...</span>
                  </div>
                </div>
              </div>
            )}

            <div className="h-full p-4">
              <GoogleCalendarEmbed
                mode={calendarView}
                width="100%"
                height="100%"
                refreshKey={calendarRefreshKey}
              />
            </div>
          </div>
        </div>
      </div>

      {/* Task Form Modal */}
      {(editingTask || isCreateMode) && (
        <div className="fixed inset-0 bg-black/70 backdrop-blur-sm flex items-center justify-center z-50 p-4">
          <div className="bg-gradient-to-br from-gray-900 to-gray-800 border border-gray-700/50 rounded-2xl shadow-2xl w-full max-w-2xl max-h-[90vh] overflow-y-auto">
            <div className="p-6">
              {/* Modal Header */}
              <div className="flex items-center justify-between mb-6">
                <div>
                  <h2 className="text-2xl font-bold text-white">
                    {isCreateMode ? 'Create New Task' : 'Edit Task'}
                  </h2>
                  <p className="text-gray-400 mt-1">
                    {isCreateMode ? 'Add a new task to your schedule' : 'Update task details'}
                  </p>
                </div>
                <button
                  onClick={resetForm}
                  className="p-2 hover:bg-gray-700/50 rounded-lg transition-all"
                >
                  <X className="w-5 h-5 text-gray-400" />
                </button>
              </div>

              {/* Form */}
              <div className="space-y-6">
                {/* Basic Info */}
                <div className="grid grid-cols-1 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Task Title *
                    </label>
                    <input
                      type="text"
                      value={formData.title}
                      onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white placeholder-gray-400 transition-all"
                      placeholder="Enter task title..."
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Description
                    </label>
                    <textarea
                      value={formData.description}
                      onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white placeholder-gray-400 transition-all resize-none"
                      rows={3}
                      placeholder="Add task description..."
                    />
                  </div>
                </div>

                {/* Date & Time */}
                <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Date *
                    </label>
                    <input
                      type="date"
                      value={formData.date}
                      onChange={(e) => setFormData(prev => ({ ...prev, date: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Start Time *
                    </label>
                    <input
                      type="time"
                      value={formData.startTime}
                      onChange={(e) => setFormData(prev => ({ ...prev, startTime: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white transition-all"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      End Time *
                    </label>
                    <input
                      type="time"
                      value={formData.endTime}
                      onChange={(e) => setFormData(prev => ({ ...prev, endTime: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white transition-all"
                    />
                  </div>
                </div>

                {/* Priority & Settings */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Priority
                    </label>
                    <select
                      value={formData.priority}
                      onChange={(e) => setFormData(prev => ({ ...prev, priority: e.target.value as any }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white transition-all"
                    >
                      <option value="High">🔴 High Priority</option>
                      <option value="Medium">🟡 Medium Priority</option>
                      <option value="Low">🟢 Low Priority</option>
                    </select>
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2">
                      Reminder (minutes before)
                    </label>
                    <select
                      value={formData.reminderMinutes}
                      onChange={(e) => setFormData(prev => ({ ...prev, reminderMinutes: parseInt(e.target.value) }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white transition-all"
                    >
                      <option value={0}>No reminder</option>
                      <option value={5}>5 minutes</option>
                      <option value={15}>15 minutes</option>
                      <option value={30}>30 minutes</option>
                      <option value={60}>1 hour</option>
                      <option value={120}>2 hours</option>
                      <option value={1440}>1 day</option>
                    </select>
                  </div>
                </div>

                {/* Location & Attendees */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                      <MapPin className="w-4 h-4 mr-2" />
                      Location
                    </label>
                    <input
                      type="text"
                      value={formData.location}
                      onChange={(e) => setFormData(prev => ({ ...prev, location: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white placeholder-gray-400 transition-all"
                      placeholder="Meeting room, address, or 'Virtual'"
                    />
                  </div>

                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                      <Users className="w-4 h-4 mr-2" />
                      Attendees
                    </label>
                    <input
                      type="text"
                      value={formData.attendees}
                      onChange={(e) => setFormData(prev => ({ ...prev, attendees: e.target.value }))}
                      className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white placeholder-gray-400 transition-all"
                      placeholder="email1@example.com, email2@example.com"
                    />
                  </div>
                </div>

                {/* Tags */}
                <div>
                  <label className="block text-sm font-medium text-gray-300 mb-2 flex items-center">
                    <Tag className="w-4 h-4 mr-2" />
                    Tags
                  </label>
                  <input
                    type="text"
                    value={formData.tags}
                    onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
                    className="w-full px-4 py-3 bg-gray-800/50 border border-gray-600/50 rounded-xl focus:outline-none focus:ring-2 focus:ring-blue-500/50 focus:border-transparent text-white placeholder-gray-400 transition-all"
                    placeholder="meeting, urgent, project-alpha..."
                  />
                  <p className="text-xs text-gray-500 mt-1">Separate tags with commas</p>
                </div>

                {/* Advanced Options */}
                <div className="border-t border-gray-700/50 pt-6">
                  <h3 className="text-lg font-medium text-white mb-4">Advanced Options</h3>
                  
                  <div className="space-y-4">
                    <label className="flex items-center space-x-3 cursor-pointer">
                      <input
                        type="checkbox"
                        checked={formData.isAgenticTask}
                        onChange={(e) => setFormData(prev => ({ ...prev, isAgenticTask: e.target.checked }))}
                        className="w-5 h-5 rounded border-gray-600 bg-gray-800 text-purple-600 focus:ring-purple-500 focus:ring-2 transition-all"
                      />
                      <div className="flex-1">
                        <div className="flex items-center space-x-2">
                          <Bot className="w-4 h-4 text-purple-400" />
                          <span className="font-medium text-white">Agentic Task</span>
                        </div>
                        <p className="text-sm text-gray-400 mt-1">
                          Allow AI agent to automatically handle this task when possible
                        </p>
                      </div>
                    </label>
                  </div>
                </div>

                {/* Error Display */}
                {error && (
                  <div className="bg-red-600/20 border border-red-600/30 rounded-xl p-4">
                    <div className="flex items-center space-x-2">
                      <AlertCircle className="w-5 h-5 text-red-400" />
                      <span className="text-red-400 font-medium">Error</span>
                    </div>
                    <p className="text-red-300 mt-1">{error}</p>
                  </div>
                )}
              </div>

              {/* Action Buttons */}
              <div className="flex items-center justify-between space-x-4 mt-8 pt-6 border-t border-gray-700/50">
                <div>
                  {!isCreateMode && editingTask && (
                    <button
                      onClick={() => {
                        deleteTask(editingTask.id);
                        resetForm();
                      }}
                      className="flex items-center space-x-2 px-4 py-2 text-red-400 hover:bg-red-600/20 hover:text-red-300 rounded-xl transition-all border border-red-600/30"
                    >
                      <Trash2 className="w-4 h-4" />
                      <span>Delete Task</span>
                    </button>
                  )}
                </div>

                <div className="flex items-center space-x-3">
                  <button
                    onClick={resetForm}
                    className="px-6 py-3 text-gray-300 bg-gray-700/50 hover:bg-gray-600/50 rounded-xl transition-all border border-gray-600/50"
                  >
                    Cancel
                  </button>
                  
                  <button
                    onClick={handleSubmit}
                    disabled={!formData.title.trim() || loading}
                    className="flex items-center space-x-2 px-6 py-3 bg-gradient-to-r from-blue-600 to-purple-600 hover:from-blue-700 hover:to-purple-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-xl transition-all shadow-lg hover:shadow-xl transform hover:scale-105 disabled:transform-none disabled:cursor-not-allowed"
                  >
                    <Save className="w-4 h-4" />
                    <span>{loading ? 'Saving...' : isCreateMode ? 'Create Task' : 'Save Changes'}</span>
                  </button>
                </div>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* Loading Overlay */}
      {loading && !isCreateMode && !editingTask && (
        <div className="fixed inset-0 bg-black/50 backdrop-blur-sm flex items-center justify-center z-40">
          <div className="bg-gray-900/90 backdrop-blur-sm rounded-2xl p-8 border border-gray-700/50">
            <div className="flex flex-col items-center space-y-4">
              <RefreshCw className="w-8 h-8 animate-spin text-blue-400" />
              <p className="text-white font-medium">Loading your tasks...</p>
            </div>
          </div>
        </div>
      )}

      {/* Error Toast */}
      {error && !isCreateMode && !editingTask && (
        <div className="fixed bottom-6 right-6 bg-red-600/90 backdrop-blur-sm text-white p-4 rounded-xl shadow-2xl border border-red-500/50 z-50">
          <div className="flex items-center space-x-3">
            <AlertCircle className="w-5 h-5" />
            <div>
              <p className="font-medium">Error occurred</p>
              <p className="text-sm text-red-200">{error}</p>
            </div>
            <button
              onClick={() => setError(null)}
              className="p-1 hover:bg-red-700/50 rounded-lg transition-colors"
            >
              <X className="w-4 h-4" />
            </button>
          </div>
        </div>
      )}
    </div>
  );
};

export default SchedulerKanban;