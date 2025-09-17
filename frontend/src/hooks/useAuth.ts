import { useState, useEffect } from 'react';
import { onAuthStateChanged, signInWithEmailAndPassword, createUserWithEmailAndPassword, signOut, User, UserCredential, updateProfile  } from 'firebase/auth';
import { auth } from '../firebase';
import { doc, getDoc, setDoc } from 'firebase/firestore';
import { db } from '../firebase';

export interface UserProfile {
  uid: string;
  email: string;
  displayName?: string;
  role: 'friend' | 'mentor' | 'girlfriend' | 'husband' | 'guide';
  voiceEnabled: boolean;
  selectedModel: string;
  alwaysOnTop: boolean;
  // Add other prefs from REQUIRED_PROFILE_KEYS
  Name?: string;
  Location?: string;
  // ... etc.
}

export const useAuth = () => {
  const [user, setUser] = useState<User | null>(null);
  const [profile, setProfile] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);
  const [idToken, setIdToken] = useState<string | null>(null);

  useEffect(() => {
    const unsubscribe = onAuthStateChanged(auth, async (firebaseUser) => {
      setUser(firebaseUser);
      if (firebaseUser) {
        const token = await firebaseUser.getIdToken();
        setIdToken(token);
        // Fetch profile
        const profileDoc = await getDoc(doc(db, 'users', firebaseUser.uid));
        if (profileDoc.exists()) {
          const data = profileDoc.data() as UserProfile;
          setProfile({ ...data, uid: firebaseUser.uid });
        } else {
          // Create default profile
          const defaultProfile: UserProfile = {
            uid: firebaseUser.uid,
            email: firebaseUser.email!,
            role: 'guide' as const,
            voiceEnabled: true,
            selectedModel: 'whisper-base',
            alwaysOnTop: false,
            // Defaults for others
            Name: firebaseUser.displayName || 'User',
          };
          await setDoc(doc(db, 'users', firebaseUser.uid), defaultProfile);
          setProfile(defaultProfile);
        }
      } else {
        setProfile(null);
        setIdToken(null);
      }
      setLoading(false);
    });
    return unsubscribe;
  }, []);

  const login = async (email: string, password: string) => {
    try {
      await signInWithEmailAndPassword(auth, email, password);
    } catch (error) {
      throw new Error((error as Error).message);
    }
  };

  const signup = async (email: string, password: string, displayName?: string) => {
    try {
      const userCredential: UserCredential = await createUserWithEmailAndPassword(auth, email, password);
      // Fixed: Use user.updateProfile for displayName
      if (displayName) {
      // FIXED: use imported updateProfile instead of user.updateProfile
      await updateProfile(userCredential.user, { displayName });
    }
      // Backend will create profile on first login
    } catch (error) {
      throw new Error((error as Error).message);
    }
  };

  const logout = async () => {
    await signOut(auth);
  };

  const updateUserProfile  = async (updates: Partial<UserProfile>) => {
    if (!profile) return;
    await setDoc(doc(db, 'users', profile.uid), { ...profile, ...updates }, { merge: true });
    setProfile({ ...profile, ...updates });
  };

  return { user, profile, loading, idToken, login, signup, logout, updateUserProfile };
};