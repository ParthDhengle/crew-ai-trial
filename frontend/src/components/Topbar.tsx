import React, { useState } from 'react';
import { motion } from 'framer-motion';
import {
  Search,
  Mic,
  MicOff,
  User,
  Settings,
  MoreVertical,
  Bot,
  Heart,
  Briefcase,
  BookOpen,
  Shield,
  Menu,
  LogOut, 
  HelpCircle
} from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
  SelectLabel,
  SelectGroup,
} from '@/components/ui/select';
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu';
import { Badge } from '@/components/ui/badge';
import { useNova } from '@/context/NovaContext';
import { useAuth } from '@/context/AuthContext'; // NEW: Import AuthContext for logout
import { useNavigate } from 'react-router-dom';
import type { NovaRole } from '@/api/types';
import { Minimize2, Maximize2, X } from 'lucide-react';
/**
 * Nova Topbar - Role switching, search, and voice controls
 *
 * Features:
 * - Role selector (friend, mentor, girlfriend, husband, guide)
 * - Global search across chats
 * - Voice enable/disable toggle
 * - Privacy indicators
 * - Quick settings access
 * - Current session info
 * - NEW: Optional children for hamburger (passed from MainLayout)
 */
interface TopbarProps {
  className?: string;
  showSearch?: boolean;
  children?: React.ReactNode; // NEW: For hamburger button
}
export default function Topbar({
  className = '',
  showSearch = true,
  children // NEW: Render children (hamburger)
}: TopbarProps) {
  const { state, dispatch } = useNova();
  const { logout } = useAuth(); // NEW: Get logout from AuthContext
  const navigate = useNavigate();
  const [searchQuery, setSearchQuery] = useState('');
  const [isSearchFocused, setIsSearchFocused] = useState(false);
  // Role configurations
  const roleConfig = {
    friend: {
      icon: User,
      label: 'Friend',
      description: 'Casual and supportive',
      color: 'text-blue-400',
    },
    mentor: {
      icon: BookOpen,
      label: 'Mentor',
      description: 'Guidance and wisdom',
      color: 'text-purple-400',
    },
    girlfriend: {
      icon: Heart,
      label: 'Girlfriend',
      description: 'Loving and caring',
      color: 'text-pink-400',
    },
    husband: {
      icon: Shield,
      label: 'Husband',
      description: 'Protective and reliable',
      color: 'text-green-400',
    },
    guide: {
      icon: Bot,
      label: 'Guide',
      description: 'Professional assistant',
      color: 'text-cyan-400',
    },
  };
  const currentRoleConfig = roleConfig[state.role];
  const RoleIcon = currentRoleConfig.icon;
  // Handle role change
  const handleRoleChange = (role: NovaRole) => {
    dispatch({ type: 'SET_ROLE', payload: role });
    // TODO: IMPLEMENT IN PRELOAD - window.api.updateUserPreferences({ role })
  };
  // Handle voice toggle
  const handleVoiceToggle = () => {
    dispatch({ type: 'SET_VOICE_ENABLED', payload: !state.voiceEnabled });
    // TODO: IMPLEMENT IN PRELOAD - window.api.updateUserPreferences({ voiceEnabled: !state.voiceEnabled })
  };
  // Handle search
  const handleSearch = (query: string) => {
    setSearchQuery(query);
    // TODO: IMPLEMENT IN PRELOAD - window.api.searchChats(query)
    console.log('Searching for:', query);
  };
  // Handle search submission
  const handleSearchSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    if (searchQuery.trim()) {
      // TODO: Implement global search functionality
      console.log('Search submitted:', searchQuery);
    }
  };

  // NEW: Handle logout
  const handleLogout = () => {
    logout(); // Clear auth
    navigate('/'); // Redirect to login/root
  };

  // NEW: Handle other menu actions (placeholders)
  const handleSettings = () => {
    dispatch({ type: 'SET_VIEW', payload: 'settings' });
  };

  const handleProfile = () => {
    // TODO: Navigate to profile view or open modal
    console.log('Open Profile');
  };

  const handleHelp = () => {
    // TODO: Open help docs or modal
    console.log('Open Help');
  };

  return (
    <div className={`border-b border-border bg-background/80 backdrop-blur-sm ${className}`}>
      <div className="flex items-center justify-between px-6 py-3">
        {/* Left Section - Role & Session Info + Hamburger */}
        <div className="flex items-center gap-4">
          {/* NEW: Render children (hamburger) here */}
          {children}
          
          {/* Role Selector */}
          <Select value={state.role} onValueChange={(value: NovaRole) => handleRoleChange(value)}>
            <SelectTrigger className="w-48 h-9 glass-nova border-primary/20 hover:border-primary/40">
              <div className="flex items-center gap-2">
                <RoleIcon size={16} className={currentRoleConfig.color} />
                <div className="flex flex-col items-start">
                  <span className="text-sm font-medium">{currentRoleConfig.label}</span>
                  <span className="text-xs text-muted-foreground -mt-0.5">
                    {currentRoleConfig.description}
                  </span>
                </div>
              </div>
            </SelectTrigger>
            <SelectContent>
              <SelectGroup>
                <SelectLabel>Choose Nova's Role</SelectLabel>
                {Object.entries(roleConfig).map(([key, config]) => {
                  const Icon = config.icon;
                  return (
                    <SelectItem key={key} value={key}>
                      <div className="flex items-center gap-2">
                        <Icon size={16} className={config.color} />
                        <div className="flex flex-col">
                          <span className="font-medium">{config.label}</span>
                          <span className="text-xs text-muted-foreground">
                            {config.description}
                          </span>
                        </div>
                      </div>
                    </SelectItem>
                  );
                })}
              </SelectGroup>
            </SelectContent>
          </Select>
          {/* Session Info */}
          {state.currentSession && (
            <div className="flex items-center gap-2 text-sm text-muted-foreground">
              <span>•</span>
              <span className="font-medium text-foreground">
                {state.currentSession.title}
              </span>
              <span>•</span>
              <span>{state.currentSession.messages.length} messages</span>
            </div>
          )}
        </div>
        {/* Center Section - Search */}
        {showSearch && (
          <motion.div
            className="flex-1 max-w-md mx-8"
            animate={{
              width: isSearchFocused ? '100%' : 'auto'
            }}
            transition={{ type: 'spring', stiffness: 300, damping: 30 }}
          >
            <form onSubmit={handleSearchSubmit} className="relative">
              <Search
                className="absolute left-3 top-1/2 transform -translate-y-1/2 text-muted-foreground"
                size={16}
              />
              <Input
                placeholder="Search conversations..."
                value={searchQuery}
                onChange={(e) => handleSearch(e.target.value)}
                onFocus={() => setIsSearchFocused(true)}
                onBlur={() => setIsSearchFocused(false)}
                className="pl-10 input-nova h-9 bg-background/50"
              />
             
              {/* Search Results Dropdown */}
              {searchQuery && isSearchFocused && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="absolute top-full left-0 right-0 mt-2 glass-nova rounded-lg border border-border shadow-lg z-50"
                >
                  <div className="p-3 text-sm text-muted-foreground">
                    Search results for "{searchQuery}"
                  </div>
                  <div className="p-2 text-xs text-muted-foreground border-t border-border">
                    Press Enter to search all conversations
                  </div>
                </motion.div>
              )}
            </form>
          </motion.div>
        )}
        {/* Right Section - Controls */}
        <div className="flex items-center gap-2">
          {/* Voice Control - existing */}
          <Button
            size="sm"
            variant={state.voiceEnabled ? 'default' : 'outline'}
            onClick={handleVoiceToggle}
            className={`gap-2 ${state.voiceEnabled ? 'btn-nova' : 'btn-nova-ghost'}`}
          >
            {state.voiceEnabled ? (
              <>
                <Mic size={14} />
                <span>Voice On</span>
              </>
            ) : (
              <>
                <MicOff size={14} />
                <span>Voice Off</span>
              </>
            )}
          </Button>
          {/* Privacy Indicator - existing */}
          <Badge
            variant="outline"
            className="bg-green-500/10 text-green-400 border-green-500/20 text-xs"
          >
            LOCAL
          </Badge>
          {/* Operations Status */}
          {state.operations.length > 0 && (
            <motion.div
              initial={{ scale: 0 }}
              animate={{ scale: 1 }}
              className="relative"
            >
              <Badge
                variant="outline"
                className="bg-primary/10 text-primary border-primary/20 animate-pulse"
              >
                {state.operations.length} Active
              </Badge>
            </motion.div>
          )}
          
          {/* NEW: User Menu */}
          <DropdownMenu>
            <DropdownMenuTrigger asChild>
              <Button size="sm" variant="ghost" className="w-9 h-9 p-0">
                <User size={18} />
              </Button>
            </DropdownMenuTrigger>
            <DropdownMenuContent align="end" className="w-48">
              <DropdownMenuLabel>My Account</DropdownMenuLabel>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleProfile}>
                <User className="mr-2 h-4 w-4" />
                <span>Profile</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleSettings}>
                <Settings className="mr-2 h-4 w-4" />
                <span>Settings</span>
              </DropdownMenuItem>
              <DropdownMenuItem onClick={handleHelp}>
                <HelpCircle className="mr-2 h-4 w-4" />
                <span>Help</span>
              </DropdownMenuItem>
              <DropdownMenuSeparator />
              <DropdownMenuItem onClick={handleLogout} className="text-destructive focus:text-destructive">
                <LogOut className="mr-2 h-4 w-4" />
                <span>Logout</span>
              </DropdownMenuItem>
            </DropdownMenuContent>
          </DropdownMenu>
        
        </div>
      </div>
    </div>
  );
}