'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

/* ─── Types ─── */
export interface UserProfile {
  fullName: string;
  email: string;
  phone: string;
  age: string;
  gender: string;
  maritalStatus: string;
  dependents: string;
  education: string;
  employment: string;
  monthlyIncome: string;
  additionalIncome: string;
  address: string;
  profileCompleted: boolean;
  existingInstallments?: string;
}

export interface User {
  id: string;
  email: string;
  password: string; // In real app, never store plain text
  fullName: string;
  createdAt: string;
  profile: UserProfile;
}

export interface PredictionResult {
  id: string;
  date: string;
  loanAmount: string;
  loanTerm: string;
  interestRate: string;
  result: 'LAYAK' | 'TIDAK LAYAK';
  confidence: number;
  inputData: Record<string, string>;
  // ── Hasil dari ML model (jika LAYAK) ──
  plafon?: number;
  bungaPersen?: string;
  bungaRate?: number;
  cicilanPerBulan?: number;
  totalBunga?: number;
  totalBayar?: number;
  sisaPlafon?: number;
  nominalDicairkan?: number;
  catatanRisiko?: string;
  // ── Jika TIDAK LAYAK ──
  alasanPenolakan?: string[];
}

interface AuthContextType {
  user: User | null;
  isLoggedIn: boolean;
  isLoading: boolean;
  predictions: PredictionResult[];
  login: (email: string, password: string) => { success: boolean; error?: string };
  register: (email: string, password: string, fullName: string) => { success: boolean; error?: string };
  logout: () => void;
  updateProfile: (profile: Partial<UserProfile>) => void;
  addPrediction: (prediction: PredictionResult) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [predictions, setPredictions] = useState<PredictionResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load from localStorage on mount
  useEffect(() => {
    try {
      const savedSession = localStorage.getItem('mlops_session');
      if (savedSession) {
        const sessionData = JSON.parse(savedSession);
        setUser(sessionData.user);
        
        const savedPredictions = localStorage.getItem(`mlops_predictions_${sessionData.user.id}`);
        if (savedPredictions) {
          setPredictions(JSON.parse(savedPredictions));
        }
      }
    } catch (e) {
      console.error('Failed to load session:', e);
    }
    setIsLoading(false);
  }, []);

  const register = useCallback((email: string, password: string, fullName: string) => {
    try {
      // Check existing users
      const existingUsers = JSON.parse(localStorage.getItem('mlops_users') || '[]') as User[];
      if (existingUsers.find(u => u.email.toLowerCase() === email.toLowerCase())) {
        return { success: false, error: 'Email sudah terdaftar' };
      }

      const newUser: User = {
        id: `user_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`,
        email: email.toLowerCase(),
        password, // In real app, hash this
        fullName,
        createdAt: new Date().toISOString(),
        profile: {
          fullName,
          email: email.toLowerCase(),
          phone: '',
          age: '',
          gender: '',
          maritalStatus: '',
          dependents: '',
          education: '',
          employment: '',
          monthlyIncome: '',
          additionalIncome: '',
          address: '',
          profileCompleted: false,
          existingInstallments: '0',
        },
      };

      existingUsers.push(newUser);
      localStorage.setItem('mlops_users', JSON.stringify(existingUsers));
      localStorage.setItem('mlops_session', JSON.stringify({ user: newUser }));
      setUser(newUser);

      return { success: true };
    } catch (e) {
      return { success: false, error: 'Gagal membuat akun' };
    }
  }, []);

  const login = useCallback((email: string, password: string) => {
    try {
      const existingUsers = JSON.parse(localStorage.getItem('mlops_users') || '[]') as User[];
      const found = existingUsers.find(
        u => u.email.toLowerCase() === email.toLowerCase() && u.password === password
      );

      if (!found) {
        return { success: false, error: 'Email atau password salah' };
      }

      localStorage.setItem('mlops_session', JSON.stringify({ user: found }));
      setUser(found);

      // Load predictions
      const savedPredictions = localStorage.getItem(`mlops_predictions_${found.id}`);
      if (savedPredictions) {
        setPredictions(JSON.parse(savedPredictions));
      } else {
        setPredictions([]);
      }

      return { success: true };
    } catch (e) {
      return { success: false, error: 'Gagal login' };
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('mlops_session');
    setUser(null);
    setPredictions([]);
  }, []);

  const updateProfile = useCallback((profileUpdate: Partial<UserProfile>) => {
    if (!user) return;

    const updatedUser = {
      ...user,
      profile: { ...user.profile, ...profileUpdate },
    };

    // Update in users list
    const existingUsers = JSON.parse(localStorage.getItem('mlops_users') || '[]') as User[];
    const idx = existingUsers.findIndex(u => u.id === user.id);
    if (idx >= 0) {
      existingUsers[idx] = updatedUser;
      localStorage.setItem('mlops_users', JSON.stringify(existingUsers));
    }

    localStorage.setItem('mlops_session', JSON.stringify({ user: updatedUser }));
    setUser(updatedUser);
  }, [user]);

  const addPrediction = useCallback((prediction: PredictionResult) => {
    if (!user) return;
    
    setPredictions(prev => {
      const updated = [prediction, ...prev];
      localStorage.setItem(`mlops_predictions_${user.id}`, JSON.stringify(updated));
      return updated;
    });
  }, [user]);

  return (
    <AuthContext.Provider value={{
      user,
      isLoggedIn: !!user,
      isLoading,
      predictions,
      login,
      register,
      logout,
      updateProfile,
      addPrediction,
    }}>
      {children}
    </AuthContext.Provider>
  );
}

export function useAuth() {
  const ctx = useContext(AuthContext);
  if (!ctx) throw new Error('useAuth must be used within AuthProvider');
  return ctx;
}
