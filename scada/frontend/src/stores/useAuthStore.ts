/**
 * Auth Store — JWT token + user info management
 * ================================================
 * Uses zustand for state management, persists token in localStorage.
 */

import { create } from 'zustand';

export type UserRole = 'admin' | 'operator' | 'viewer';

export interface AuthUser {
  username: string;
  role: UserRole;
  displayName: string;
}

interface AuthStore {
  token: string | null;
  user: AuthUser | null;
  isAuthenticated: boolean;
  isLoading: boolean;
  error: string | null;

  login: (username: string, password: string) => Promise<boolean>;
  logout: () => void;
  checkAuth: () => void;
}

const API_BASE = 'http://localhost:4000';

export const useAuthStore = create<AuthStore>((set, get) => ({
  token: localStorage.getItem('scada_token'),
  user: JSON.parse(localStorage.getItem('scada_user') || 'null'),
  isAuthenticated: !!localStorage.getItem('scada_token'),
  isLoading: false,
  error: null,

  login: async (username: string, password: string) => {
    set({ isLoading: true, error: null });
    try {
      const res = await fetch(`${API_BASE}/api/auth/login`, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ username, password }),
      });

      if (!res.ok) {
        const data = await res.json().catch(() => ({ error: 'Login failed' }));
        set({ isLoading: false, error: data.error || 'Login failed' });
        return false;
      }

      const data = await res.json();
      localStorage.setItem('scada_token', data.token);
      localStorage.setItem('scada_user', JSON.stringify(data.user));
      set({
        token: data.token,
        user: data.user,
        isAuthenticated: true,
        isLoading: false,
        error: null,
      });
      return true;
    } catch (e: any) {
      set({ isLoading: false, error: 'Connection failed' });
      return false;
    }
  },

  logout: () => {
    localStorage.removeItem('scada_token');
    localStorage.removeItem('scada_user');
    set({ token: null, user: null, isAuthenticated: false, error: null });
  },

  checkAuth: () => {
    const token = localStorage.getItem('scada_token');
    const user = JSON.parse(localStorage.getItem('scada_user') || 'null');
    if (token && user) {
      set({ token, user, isAuthenticated: true });
    } else {
      set({ token: null, user: null, isAuthenticated: false });
    }
  },
}));
