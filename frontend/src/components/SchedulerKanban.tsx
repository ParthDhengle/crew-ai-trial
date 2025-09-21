import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import {
  DndContext,
  DragEndEvent,
  DragOverlay,
  DragStartEvent,
  closestCenter,
  KeyboardSensor,
  PointerSensor,
  useSensor,
  useSensors,
} from '@dnd-kit/core';
import {
  arrayMove,
  SortableContext,
  sortableKeyboardCoordinates,
  verticalListSortingStrategy,
} from '@dnd-kit/sortable';
import {
  useSortable,
} from '@dnd-kit/sortable';
import { CSS } from '@dnd-kit/utilities';
import {
  Plus,
  Calendar,
  AlertTriangle,
  Clock,
  MoreVertical,
  Edit,
  Trash2,
  Flag,
  Bot
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Badge } from '@/components/ui/badge';
import { 
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogTrigger,
} from '@/components/ui/dialog';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
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
import { Switch } from '@/components/ui/switch';
import { useNova } from '@/context/NovaContext';
import type { SchedulerTask } from '@/api/types';

/**
 * Nova Scheduler Kanban - Task management with drag & drop
 * 
 * Features:
 * - Three columns: To Do, In Progress, Done
 * - Drag & drop between columns
 * - Task creation and editing
 * - Priority levels (High, Medium, Low)
 * - Deadline tracking
 * - Agentic task toggle
 * - Quick actions (reschedule, mark done, convert to event)
 * - Beautiful animations with Framer Motion
 */

type ColumnType = 'todo' | 'inprogress' | 'done';

interface ColumnConfig {
  id: ColumnType;
  title: string;
  color: string;
  bgColor: string;
  borderColor: string;
}

const columns: ColumnConfig[] = [
  {
    id: 'todo',
    title: 'To Do',
    color: 'text-blue-400',
    bgColor: 'bg-blue-400/5',
    borderColor: 'border-blue-400/20',
  },
  {
    id: 'inprogress',
    title: 'In Progress',
    color: 'text-yellow-400',
    bgColor: 'bg-yellow-400/5',
    borderColor: 'border-yellow-400/20',
  },
  {
    id: 'done',
    title: 'Done',
    color: 'text-green-400',
    bgColor: 'bg-green-400/5',
    borderColor: 'border-green-400/20',
  },
];

interface TaskCardProps {
  task: SchedulerTask;
  isDragging?: boolean;
  onEdit: (task: SchedulerTask) => void;
  onDelete: (taskId: string) => void;
  onQuickAction: (action: string, task: SchedulerTask) => void;
}

function TaskCard({ task, isDragging, onEdit, onDelete, onQuickAction }: TaskCardProps) {
  const {
    attributes,
    listeners,
    setNodeRef,
    transform,
    transition,
    isDragging: isSortableDragging,
  } = useSortable({ id: task.id });

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
  };

  const priorityConfig = {
    High: { color: 'text-red-400', bg: 'bg-red-400/10', border: 'border-red-400/20' },
    Medium: { color: 'text-yellow-400', bg: 'bg-yellow-400/10', border: 'border-yellow-400/20' },
    Low: { color: 'text-green-400', bg: 'bg-green-400/10', border: 'border-green-400/20' },
  };

  const priority = priorityConfig[task.priority];
  const isOverdue = new Date(task.deadline) < new Date();
  const isDueSoon = new Date(task.deadline) < new Date(Date.now() + 24 * 60 * 60 * 1000);

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className={`card-nova p-4 cursor-grab active:cursor-grabbing group ${
        isSortableDragging || isDragging ? 'opacity-50 rotate-2 scale-105' : ''
      }`}
    >
      {/* Task Header */}
      <div className="flex items-start justify-between mb-3">
        <div className="flex-1 min-w-0">
          <div className="font-medium text-sm truncate">
            {task.title}
          </div>
          {task.description && (
            <div className="text-xs text-muted-foreground mt-1 line-clamp-2">
              {task.description}
            </div>
          )}
        </div>

        <div className="flex items-center gap-1 opacity-0 group-hover:opacity-100 transition-opacity">
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button
                size="sm"
                variant="ghost"
                className="w-6 h-6 p-0"
                onClick={(e) => e.stopPropagation()}
              >
                <MoreVertical size={12} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end">
              <DropdownMenuItem onClick={() => onEdit(task)}>
                <Edit className="mr-2 h-3 w-3" />
                Edit Task
              </DropdownMenuItem>
              <DropdownMenuItem onClick={() => onQuickAction('reschedule', task)}>
                <Calendar className="mr-2 h-3 w-3" />
                Reschedule
              </DropdownMenuItem>
              {task.status !== 'done' && (
                <DropdownMenuItem onClick={() => onQuickAction('markDone', task)}>
                  <Flag className="mr-2 h-3 w-3" />
                  Mark Done
                </DropdownMenuItem>
              )}
              <DropdownMenuItem 
                className="text-destructive"
                onClick={() => onDelete(task.id)}
              >
                <Trash2 className="mr-2 h-3 w-3" />
                Delete
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        </div>
      </div>

      {/* Task Meta */}
      <div className="space-y-2">
        {/* Priority & Status */}
        <div className="flex items-center gap-2">
          <Badge 
            variant="outline"
            className={`text-xs ${priority.color} ${priority.bg} ${priority.border}`}
          >
            {task.priority}
          </Badge>
          
          {task.isAgenticTask && (
            <Badge variant="outline" className="text-xs bg-primary/10 text-primary border-primary/20">
              <Bot size={8} className="mr-1" />
              AI
            </Badge>
          )}
        </div>

        {/* Deadline */}
        <div className={`flex items-center gap-1 text-xs ${
          isOverdue ? 'text-red-400' : isDueSoon ? 'text-yellow-400' : 'text-muted-foreground'
        }`}>
          <Clock size={10} />
          <span>
            {new Date(task.deadline).toLocaleDateString()} at{' '}
            {new Date(task.deadline).toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}
          </span>
          {isOverdue && <AlertTriangle size={10} className="text-red-400" />}
        </div>

        {/* Tags */}
        {task.tags && task.tags.length > 0 && (
          <div className="flex flex-wrap gap-1">
            {task.tags.slice(0, 2).map((tag) => (
              <Badge key={tag} variant="secondary" className="text-xs px-1.5 py-0">
                {tag}
              </Badge>
            ))}
            {task.tags.length > 2 && (
              <Badge variant="secondary" className="text-xs px-1.5 py-0">
                +{task.tags.length - 2}
              </Badge>
            )}
          </div>
        )}
      </div>
    </div>
  );
}

interface TaskEditDialogProps {
  task?: SchedulerTask;
  open: boolean;
  onOpenChange: (open: boolean) => void;
  onSave: (task: Partial<SchedulerTask>) => void;
}

function TaskEditDialog({ task, open, onOpenChange, onSave }: TaskEditDialogProps) {
  const [formData, setFormData] = useState({
    title: task?.title || '',
    description: task?.description || '',
    deadline: task?.deadline ? new Date(task.deadline).toISOString().slice(0, 16) : '',
    priority: task?.priority || 'Medium' as const,
    tags: task?.tags?.join(', ') || '',
    isAgenticTask: task?.isAgenticTask || false,
  });

  const handleSave = () => {
    if (!formData.title.trim()) return;

    onSave({
      ...task,
      title: formData.title.trim(),
      description: formData.description.trim(),
      deadline: new Date(formData.deadline).toISOString(),
      priority: formData.priority,
      tags: formData.tags.split(',').map(t => t.trim()).filter(Boolean),
      isAgenticTask: formData.isAgenticTask,
    });

    onOpenChange(false);
  };

  return (
    <Dialog open={open} onOpenChange={onOpenChange}>
      <DialogContent className="sm:max-w-md">
        <DialogHeader>
          <DialogTitle>
            {task ? 'Edit Task' : 'Create New Task'}
          </DialogTitle>
        </DialogHeader>

        <div className="space-y-4">
          <div>
            <Label htmlFor="title">Title</Label>
            <Input
              id="title"
              value={formData.title}
              onChange={(e) => setFormData(prev => ({ ...prev, title: e.target.value }))}
              placeholder="Task title..."
              className="mt-1"
            />
          </div>

          <div>
            <Label htmlFor="description">Description</Label>
            <Textarea
              id="description"
              value={formData.description}
              onChange={(e) => setFormData(prev => ({ ...prev, description: e.target.value }))}
              placeholder="Task description..."
              className="mt-1 min-h-[80px]"
            />
          </div>

          <div className="grid grid-cols-2 gap-4">
            <div>
              <Label htmlFor="deadline">Deadline</Label>
              <Input
                id="deadline"
                type="datetime-local"
                value={formData.deadline}
                onChange={(e) => setFormData(prev => ({ ...prev, deadline: e.target.value }))}
                className="mt-1"
              />
            </div>

            <div>
              <Label htmlFor="priority">Priority</Label>
              <Select
                value={formData.priority}
                onValueChange={(value: 'High' | 'Medium' | 'Low') => setFormData(prev => ({ ...prev, priority: value }))} // Fixed: Specific type
              >
                <SelectTrigger className="mt-1">
                  <SelectValue />
                </SelectTrigger>
                <SelectContent>
                  <SelectItem value="High">High Priority</SelectItem>
                  <SelectItem value="Medium">Medium Priority</SelectItem>
                  <SelectItem value="Low">Low Priority</SelectItem>
                </SelectContent>
              </Select>
            </div>
          </div>

          <div>
            <Label htmlFor="tags">Tags (comma-separated)</Label>
            <Input
              id="tags"
              value={formData.tags}
              onChange={(e) => setFormData(prev => ({ ...prev, tags: e.target.value }))}
              placeholder="project, urgent, personal..."
              className="mt-1"
            />
          </div>

          <div className="flex items-center space-x-2">
            <Switch
              id="agentic"
              checked={formData.isAgenticTask}
              onCheckedChange={(checked) => setFormData(prev => ({ ...prev, isAgenticTask: checked }))}
            />
            <Label htmlFor="agentic" className="text-sm">
              Make this an Agentic Task
            </Label>
          </div>

          <div className="flex gap-2 pt-4">
            <Button onClick={handleSave} className="flex-1 btn-nova">
              {task ? 'Update Task' : 'Create Task'}
            </Button>
            <Button variant="outline" onClick={() => onOpenChange(false)}>
              Cancel
            </Button>
          </div>
        </div>
      </DialogContent>
    </Dialog>
  );
}

export default function SchedulerKanban() {
  const { state, dispatch } = useNova();
  const [activeTask, setActiveTask] = useState<SchedulerTask | null>(null);
  const [editingTask, setEditingTask] = useState<SchedulerTask | undefined>();
  const [showEditDialog, setShowEditDialog] = useState(false);

  const sensors = useSensors(
    useSensor(PointerSensor),
    useSensor(KeyboardSensor, {
      coordinateGetter: sortableKeyboardCoordinates,
    })
  );

  // Group tasks by status
  const tasksByStatus = state.tasks.reduce((acc, task) => {
    acc[task.status] = acc[task.status] || [];
    acc[task.status].push(task);
    return acc;
  }, {} as Record<ColumnType, SchedulerTask[]>);

  // Handle drag start
  const handleDragStart = (event: DragStartEvent) => {
    const task = state.tasks.find(t => t.id === event.active.id);
    setActiveTask(task || null);
  };

  // Handle drag end
  const handleDragEnd = (event: DragEndEvent) => {
    const { active, over } = event;
    setActiveTask(null);

    if (!over) return;

    const taskId = active.id as string;
    const newStatus = over.id as ColumnType;

    // Update task status
    dispatch({
      type: 'UPDATE_TASK',
      payload: {
        id: taskId,
        updates: { status: newStatus }
      }
    });
  };

  // Handle task creation/editing
  const handleSaveTask = (taskData: Partial<SchedulerTask>) => {
    if (editingTask) {
      // Update existing task
      dispatch({
        type: 'UPDATE_TASK',
        payload: {
          id: editingTask.id,
          updates: taskData
        }
      });
    } else {
      // Create new task
      const newTask: SchedulerTask = {
        id: `task-${Date.now()}`,
        title: taskData.title!,
        description: taskData.description || '',
        deadline: taskData.deadline!,
        priority: taskData.priority!,
        status: 'todo',
        tags: taskData.tags || [],
        isAgenticTask: taskData.isAgenticTask || false,
        createdAt: new Date().toISOString(),
        updatedAt: new Date().toISOString(),
      };

      dispatch({ type: 'ADD_TASK', payload: newTask });
    }

    setEditingTask(undefined);
  };

  // Handle task deletion
  const handleDeleteTask = (taskId: string) => {
    dispatch({ type: 'DELETE_TASK', payload: taskId });
  };

  // Handle quick actions
  const handleQuickAction = (action: string, task: SchedulerTask) => {
    switch (action) {
      case 'reschedule':
        // TODO: Open reschedule dialog
        console.log('Rescheduling task:', task.id);
        break;
      case 'markDone':
        dispatch({
          type: 'UPDATE_TASK',
          payload: {
            id: task.id,
            updates: { status: 'done' }
          }
        });
        break;
      default:
        console.log('Unknown action:', action);
    }
  };

  // Open task creation dialog
  const openCreateDialog = () => {
    setEditingTask(undefined);
    setShowEditDialog(true);
  };

  // Open task edit dialog
  const openEditDialog = (task: SchedulerTask) => {
    setEditingTask(task);
    setShowEditDialog(true);
  };

  return (
    <div className="h-full flex flex-col bg-background">
      {/* Header */}
      <div className="p-6 border-b border-border">
        <div className="flex items-center justify-between">
          <div>
            <h1 className="text-2xl font-bold">Task Scheduler</h1>
            <p className="text-muted-foreground">
              Organize your tasks with drag & drop kanban board
            </p>
          </div>
          <Button onClick={openCreateDialog} className="btn-nova gap-2">
            <Plus size={16} />
            New Task
          </Button>
        </div>
      </div>

      {/* Kanban Board */}
      <div className="flex-1 p-6">
        <DndContext
          sensors={sensors}
          collisionDetection={closestCenter}
          onDragStart={handleDragStart}
          onDragEnd={handleDragEnd}
        >
          <div className="grid grid-cols-3 gap-6 h-full">
            {columns.map((column) => (
              <div
                key={column.id}
                className={`flex flex-col rounded-xl border-2 ${column.borderColor} ${column.bgColor} p-4`}
              >
                {/* Column Header */}
                <div className="flex items-center justify-between mb-4">
                  <div className="flex items-center gap-2">
                    <h3 className={`font-semibold ${column.color}`}>
                      {column.title}
                    </h3>
                    <Badge variant="secondary" className="text-xs">
                      {tasksByStatus[column.id]?.length || 0}
                    </Badge>
                  </div>
                </div>

                {/* Task List */}
                <SortableContext
                  items={tasksByStatus[column.id]?.map(t => t.id) || []}
                  strategy={verticalListSortingStrategy}
                >
                  <div className="space-y-3 flex-1">
                    <AnimatePresence>
                      {tasksByStatus[column.id]?.map((task) => (
                        <motion.div
                          key={task.id}
                          layout
                          initial={{ opacity: 0, scale: 0.8 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0, scale: 0.8 }}
                        >
                          <TaskCard
                            task={task}
                            onEdit={openEditDialog}
                            onDelete={handleDeleteTask}
                            onQuickAction={handleQuickAction}
                          />
                        </motion.div>
                      ))}
                    </AnimatePresence>
                  </div>
                </SortableContext>
              </div>
            ))}
          </div>

          {/* Drag Overlay */}
          <DragOverlay>
            {activeTask ? (
              <TaskCard
                task={activeTask}
                isDragging
                onEdit={() => {}}
                onDelete={() => {}}
                onQuickAction={() => {}}
              />
            ) : null}
          </DragOverlay>
        </DndContext>
      </div>

      {/* Task Edit Dialog */}
      <TaskEditDialog
        task={editingTask}
        open={showEditDialog}
        onOpenChange={setShowEditDialog}
        onSave={handleSaveTask}
      />
    </div>
  );
}