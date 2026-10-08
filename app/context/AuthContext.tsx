'use client';

import React, { createContext, useContext, useState, useEffect, useCallback } from 'react';

const API_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

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
  login: (email: string, password: string) => Promise<{ success: boolean; error?: string }>;
  register: (email: string, password: string, fullName: string) => Promise<{ success: boolean; error?: string }>;
  logout: () => void;
  updateProfile: (profile: Partial<UserProfile>) => void;
  addPrediction: (prediction: PredictionResult) => void;
}

const AuthContext = createContext<AuthContextType | null>(null);

export function AuthProvider({ children }: { children: React.ReactNode }) {
  const [user, setUser] = useState<User | null>(null);
  const [predictions, setPredictions] = useState<PredictionResult[]>([]);
  const [isLoading, setIsLoading] = useState(true);

  // Load session from localStorage on mount, then fetch profile from API
  useEffect(() => {
    const loadSession = async () => {
      try {
        const savedSession = localStorage.getItem('mlops_session');
        if (savedSession) {
          const sessionData = JSON.parse(savedSession);
          const userId = sessionData.user?.id;
          if (userId) {
            // Fetch latest profile from backend
            const res = await fetch(`${API_URL}/auth/profile/${userId}`);
            if (res.ok) {
              const data = await res.json();
              const loadedUser: User = {
                id: data.id,
                email: data.email,
                password: '', // Not stored client-side
                fullName: data.fullName,
                createdAt: data.createdAt,
                profile: data.profile,
              };
              setUser(loadedUser);
              localStorage.setItem('mlops_session', JSON.stringify({ user: loadedUser }));

              // Fetch predictions from backend
              const predRes = await fetch(`${API_URL}/auth/predictions/${userId}`);
              if (predRes.ok) {
                const predData = await predRes.json();
                setPredictions(predData.predictions || []);
              }
            } else {
              // Token/session invalid, clear
              localStorage.removeItem('mlops_session');
            }
          }
        }
      } catch (e) {
        console.error('Failed to load session:', e);
      }
      setIsLoading(false);
    };
    loadSession();
  }, []);

  const register = useCallback(async (email: string, password: string, fullName: string) => {
    try {
      const res = await fetch(`${API_URL}/auth/register`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password, fullName }),
      });

      if (!res.ok) {
        const err = await res.json();
        return { success: false, error: err.detail || 'Gagal membuat akun' };
      }

      const data = await res.json();
      const newUser: User = {
        id: data.user.id,
        email: data.user.email,
        password: '',
        fullName: data.user.fullName,
        createdAt: data.user.createdAt,
        profile: data.user.profile,
      };

      localStorage.setItem('mlops_session', JSON.stringify({ user: newUser, token: data.token }));
      setUser(newUser);
      setPredictions([]);
      return { success: true };
    } catch (e) {
      return { success: false, error: 'Gagal terhubung ke server' };
    }
  }, []);

  const login = useCallback(async (email: string, password: string) => {
    try {
      const res = await fetch(`${API_URL}/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ email, password }),
      });

      if (!res.ok) {
        const err = await res.json();
        return { success: false, error: err.detail || 'Email atau password salah' };
      }

      const data = await res.json();
      const loggedInUser: User = {
        id: data.user.id,
        email: data.user.email,
        password: '',
        fullName: data.user.fullName,
        createdAt: data.user.createdAt,
        profile: data.user.profile,
      };

      localStorage.setItem('mlops_session', JSON.stringify({ user: loggedInUser, token: data.token }));
      setUser(loggedInUser);

      // Load predictions from backend
      try {
        const predRes = await fetch(`${API_URL}/auth/predictions/${loggedInUser.id}`);
        if (predRes.ok) {
          const predData = await predRes.json();
          setPredictions(predData.predictions || []);
        }
      } catch { setPredictions([]); }

      return { success: true };
    } catch (e) {
      return { success: false, error: 'Gagal terhubung ke server' };
    }
  }, []);

  const logout = useCallback(() => {
    localStorage.removeItem('mlops_session');
    setUser(null);
    setPredictions([]);
  }, []);

  const updateProfile = useCallback(async (profileUpdate: Partial<UserProfile>) => {
    if (!user) return;

    // Optimistic update locally first
    const updatedUser = {
      ...user,
      profile: { ...user.profile, ...profileUpdate },
    };
    setUser(updatedUser);
    localStorage.setItem('mlops_session', JSON.stringify({ user: updatedUser }));

    // Then sync to backend
    try {
      await fetch(`${API_URL}/auth/profile/${user.id}`, {
        method: 'PUT',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(profileUpdate),
      });
    } catch (e) {
      console.error('Failed to sync profile to backend:', e);
    }
  }, [user]);

  const addPrediction = useCallback((prediction: PredictionResult) => {
    if (!user) return;
    setPredictions(prev => [prediction, ...prev]);
    // Note: prediction is already saved to DB by the /predict endpoint
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
