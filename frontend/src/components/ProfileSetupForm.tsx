import React, { useState } from 'react';
import { motion, AnimatePresence } from 'framer-motion';
import { ChevronRight, ChevronLeft, User, Briefcase, MapPin, Clock, Target, MessageCircle, Check, X, Minimize2, Maximize2, Minus } from 'lucide-react';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card';
import { useAuth } from '@/context/AuthContext';
import { apiClient } from '@/api/client';

interface ProfileSetupProps {
  onComplete?: () => void;
  className?: string;
}

interface ProfileData {
  name: string;
  role: string;
  customRole?: string;
  location: string;
  productiveTime: string;
  topMotivation: string;
  aiTone: string;
}

const roleOptions = [
  { value: 'student', label: 'Student', icon: '🎓' },
  { value: 'professional', label: 'Professional', icon: '💼' },
  { value: 'entrepreneur', label: 'Entrepreneur', icon: '🚀' },
  { value: 'creative', label: 'Creative', icon: '🎨' },
  { value: 'researcher', label: 'Researcher', icon: '🔬' },
  { value: 'freelancer', label: 'Freelancer', icon: '💻' },
  { value: 'manager', label: 'Manager', icon: '👔' },
  { value: 'consultant', label: 'Consultant', icon: '🎯' },
  { value: 'other', label: 'Other', icon: '⚡' }
];

const productiveTimeOptions = [
  { value: 'morning', label: 'Morning (6AM - 12PM)', icon: '🌅' },
  { value: 'afternoon', label: 'Afternoon (12PM - 6PM)', icon: '☀️' },
  { value: 'evening', label: 'Evening (6PM - 10PM)', icon: '🌆' },
  { value: 'night', label: 'Night (10PM - 6AM)', icon: '🌙' }
];

const motivationOptions = [
  { value: 'achieving_goals', label: 'Achieving Goals', description: 'Completing tasks and reaching milestones', icon: '🎯' },
  { value: 'recognition_praise', label: 'Recognition & Praise', description: 'Being acknowledged for achievements', icon: '🏆' },
  { value: 'learning_growth', label: 'Learning & Growth', description: 'Acquiring new skills and knowledge', icon: '📚' },
  { value: 'personal_satisfaction', label: 'Personal Satisfaction', description: 'Inner fulfillment and contentment', icon: '✨' }
];

const toneOptions = [
  { value: 'casual_friendly', label: 'Casual & Friendly', description: 'Relaxed, warm, and approachable', icon: '😊' },
  { value: 'professional_formal', label: 'Professional & Formal', description: 'Business-like, structured, and precise', icon: '🤝' },
  { value: 'neutral', label: 'Neutral', description: 'Balanced, informative, and objective', icon: '⚖️' }
];

export default function ProfileSetupForm({ onComplete, className = '' }: ProfileSetupProps) {
  const { user } = useAuth();
  const [currentStep, setCurrentStep] = useState(0);
  const [isSubmitting, setIsSubmitting] = useState(false);
  const [profileData, setProfileData] = useState<ProfileData>({
    name: '',
    role: '',
    customRole: '',
    location: '',
    productiveTime: '',
    topMotivation: '',
    aiTone: ''
  });

  const steps = [
    { id: 'name', title: 'What is your name?', icon: User },
    { id: 'role', title: 'What is your role or occupation?', icon: Briefcase },
    { id: 'location', title: 'Where are you located?', icon: MapPin },
    { id: 'productiveTime', title: 'When are you most productive?', icon: Clock },
    { id: 'motivation', title: 'What motivates you the most?', icon: Target },
    { id: 'tone', title: 'What tone would you prefer I use?', icon: MessageCircle }
  ];

  const handleInputChange = (field: keyof ProfileData, value: string) => {
    setProfileData(prev => ({ ...prev, [field]: value }));
  };

  const canProceed = () => {
    switch (currentStep) {
      case 0: return profileData.name.trim() !== '';
      case 1: return profileData.role !== '' && (profileData.role !== 'other' || profileData.customRole?.trim());
      case 2: return profileData.location.trim() !== '';
      case 3: return profileData.productiveTime !== '';
      case 4: return profileData.topMotivation !== '';
      case 5: return profileData.aiTone !== '';
      default: return false;
    }
  };

  const handleNext = () => {
    if (currentStep < steps.length - 1) {
      setCurrentStep(currentStep + 1);
    }
  };

  const handlePrev = () => {
    if (currentStep > 0) {
      setCurrentStep(currentStep - 1);
    }
  };

  const handleSubmit = async () => {
    if (!user) return;
    
    setIsSubmitting(true);
    try {
      const profileUpdates = {
        Name: profileData.name,
        display_name: profileData.name,
        role: profileData.role === 'other' ? profileData.customRole : profileData.role,
        location: profileData.location,
        productive_time: profileData.productiveTime,
        top_motivation: profileData.topMotivation,
        ai_tone: profileData.aiTone,
        profile_completed: true,
        updated_at: new Date().toISOString()
      };

      await apiClient.completeProfile(profileUpdates);
      onComplete?.();
    } catch (error) {
      console.error('Profile setup failed:', error);
      // Handle error (maybe show a toast)
    } finally {
      setIsSubmitting(false);
    }
  };

  const renderStepContent = () => {
    switch (currentStep) {
      case 0: // Name
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <User className="w-12 h-12 mx-auto mb-3 text-primary" />
              <p className="text-muted-foreground">Help me get to know you better</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="name">Your Name</Label>
              <Input
                id="name"
                placeholder="Enter your full name"
                value={profileData.name}
                onChange={(e) => handleInputChange('name', e.target.value)}
                className="text-center"
                autoFocus
              />
            </div>
          </div>
        );

        case 1: // Role
          return (
            <div className="space-y-4">
              <div className="text-center mb-6">
                <Briefcase className="w-12 h-12 mx-auto mb-3 text-primary" />
                <p className="text-muted-foreground">This helps me understand your context</p>
              </div>
        
              {/* Scrollable role list container */}
              <div className="max-h-[40vh] overflow-auto pr-2">
                <div className="grid grid-cols-2 gap-3">
                  {roleOptions.map((option) => (
                    <Button
                      key={option.value}
                      variant={profileData.role === option.value ? "default" : "outline"}
                      className="h-auto p-4 flex flex-col items-center space-y-2 text-sm"
                      onClick={() => handleInputChange('role', option.value)}
                    >
                      <span className="text-xl">{option.icon}</span>
                      <span className="text-sm">{option.label}</span>
                    </Button>
                  ))}
                </div>
              </div>
        
              {profileData.role === 'other' && (
                <div className="space-y-2 mt-4">
                  <Label htmlFor="customRole">Please specify</Label>
                  <Input
                    id="customRole"
                    placeholder="Enter your role/occupation"
                    value={profileData.customRole || ''}
                    onChange={(e) => handleInputChange('customRole', e.target.value)}
                  />
                </div>
              )}
            </div>
          );

      case 2: // Location
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <MapPin className="w-12 h-12 mx-auto mb-3 text-primary" />
              <p className="text-muted-foreground">For timezone and location-specific assistance</p>
            </div>
            <div className="space-y-2">
              <Label htmlFor="location">Your Location</Label>
              <Input
                id="location"
                placeholder="City, Country (e.g., New York, USA)"
                value={profileData.location}
                onChange={(e) => handleInputChange('location', e.target.value)}
                className="text-center"
              />
            </div>
          </div>
        );

      case 3: // Productive Time
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <Clock className="w-12 h-12 mx-auto mb-3 text-primary" />
              <p className="text-muted-foreground">When do you do your best work?</p>
            </div>
            <div className="space-y-3">
              {productiveTimeOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={profileData.productiveTime === option.value ? "default" : "outline"}
                  className="w-full h-auto p-4 flex items-center justify-between"
                  onClick={() => handleInputChange('productiveTime', option.value)}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{option.icon}</span>
                    <span>{option.label}</span>
                  </div>
                  {profileData.productiveTime === option.value && <Check className="w-5 h-5" />}
                </Button>
              ))}
            </div>
          </div>
        );

      case 4: // Motivation
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <Target className="w-12 h-12 mx-auto mb-3 text-primary" />
              <p className="text-muted-foreground">What drives you forward?</p>
            </div>
            <div className="space-y-3">
              {motivationOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={profileData.topMotivation === option.value ? "default" : "outline"}
                  className="w-full h-auto p-4 flex items-center justify-between"
                  onClick={() => handleInputChange('topMotivation', option.value)}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{option.icon}</span>
                    <div className="text-left">
                      <div className="font-medium">{option.label}</div>
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                    </div>
                  </div>
                  {profileData.topMotivation === option.value && <Check className="w-5 h-5" />}
                </Button>
              ))}
            </div>
          </div>
        );

      case 5: // AI Tone
        return (
          <div className="space-y-4">
            <div className="text-center mb-6">
              <MessageCircle className="w-12 h-12 mx-auto mb-3 text-primary" />
              <p className="text-muted-foreground">How would you like me to communicate?</p>
            </div>
            <div className="space-y-3">
              {toneOptions.map((option) => (
                <Button
                  key={option.value}
                  variant={profileData.aiTone === option.value ? "default" : "outline"}
                  className="w-full h-auto p-4 flex items-center justify-between"
                  onClick={() => handleInputChange('aiTone', option.value)}
                >
                  <div className="flex items-center space-x-3">
                    <span className="text-xl">{option.icon}</span>
                    <div className="text-left">
                      <div className="font-medium">{option.label}</div>
                      <div className="text-xs text-muted-foreground">{option.description}</div>
                    </div>
                  </div>
                  {profileData.aiTone === option.value && <Check className="w-5 h-5" />}
                </Button>
              ))}
            </div>
          </div>
        );

      default:
        return null;
    }
  };

  return (
    <div className={`flex items-center justify-center min-h-screen bg-background ${className}`}>
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ duration: 0.5 }}
        className="w-full max-w-2xl"
      >
        {/* Window Title Bar */}
        <div 
          className="flex items-center justify-between px-4 py-2 bg-background/95 backdrop-blur-sm border-b border-border/50"
          style={{ 
            ['WebkitAppRegion' as any]: 'drag',
            userSelect: 'none'
          }}
        >
          <div className="flex items-center space-x-2">
            <span className="ml-3 text-sm font-medium text-foreground/80">
              Nova Profile Setup
            </span>
          </div>
          
          <div className="flex items-center space-x-1" style={{ ['WebkitAppRegion' as any]: 'no-drag' }}>
            <Button
              size="sm"
              variant="ghost"
              className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
              title="Minimize"
            >
              <Minus size={12} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="w-6 h-6 p-0 hover:bg-muted/50 rounded-none"
              title="Maximize"
            >
              <Maximize2 size={12} />
            </Button>
            <Button
              size="sm"
              variant="ghost"
              className="w-6 h-6 p-0 hover:bg-red-500/20 text-red-400 hover:text-red-300 rounded-none"
              title="Close"
            >
              <X size={12} />
            </Button>
          </div>
        </div>

        <Card className="glass-nova border-primary/20">
          <CardHeader className="text-center">
            <div className="w-16 h-16 bg-gradient-to-br from-primary to-accent rounded-full mx-auto mb-4 flex items-center justify-center text-2xl font-bold text-primary-foreground">
              N
            </div>
            <CardTitle className="text-2xl font-bold">Let's personalize Nova for you</CardTitle>
            <CardDescription>
              Step {currentStep + 1} of {steps.length}: {steps[currentStep].title}
            </CardDescription>
            
            {/* Progress bar */}
            <div className="w-full bg-muted rounded-full h-2 mt-4">
              <motion.div
                className="bg-primary h-2 rounded-full"
                initial={{ width: 0 }}
                animate={{ width: `${((currentStep + 1) / steps.length) * 100}%` }}
                transition={{ duration: 0.3 }}
              />
            </div>
          </CardHeader>
          
          <CardContent>
            <AnimatePresence mode="wait">
              <motion.div
                key={currentStep}
                initial={{ opacity: 0, x: 50 }}
                animate={{ opacity: 1, x: 0 }}
                exit={{ opacity: 0, x: -50 }}
                transition={{ duration: 0.3 }}
                className="min-h-[300px]"
              >
                {renderStepContent()}
              </motion.div>
            </AnimatePresence>
            
            {/* Navigation buttons */}
            <div className="flex justify-between items-center mt-8 pt-6 border-t">
              <Button
                variant="outline"
                onClick={handlePrev}
                disabled={currentStep === 0}
                className="flex items-center space-x-2"
              >
                <ChevronLeft className="w-4 h-4" />
                <span>Previous</span>
              </Button>
              
              {currentStep < steps.length - 1 ? (
                <Button
                  onClick={handleNext}
                  disabled={!canProceed()}
                  className="flex items-center space-x-2 btn-nova"
                >
                  <span>Next</span>
                  <ChevronRight className="w-4 h-4" />
                </Button>
              ) : (
                <Button
                  onClick={handleSubmit}
                  disabled={!canProceed() || isSubmitting}
                  className="flex items-center space-x-2 btn-nova"
                >
                  {isSubmitting ? (
                    <>
                      <div className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                      <span>Setting up...</span>
                    </>
                  ) : (
                    <>
                      <span>Complete Setup</span>
                      <Check className="w-4 h-4" />
                    </>
                  )}
                </Button>
              )}
            </div>
          </CardContent>
        </Card>
      </motion.div>
    </div>
  );
}