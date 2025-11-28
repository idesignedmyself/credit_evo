/**
 * Credit Engine 2.0 - Auth State Store
 * Manages authentication state with Zustand
 */
import { create } from 'zustand';

const TOKEN_KEY = 'credit_engine_token';
const USER_KEY = 'credit_engine_user';

const useAuthStore = create((set, get) => ({
  // State
  token: localStorage.getItem(TOKEN_KEY) || null,
  user: JSON.parse(localStorage.getItem(USER_KEY) || 'null'),
  isAuthenticated: !!localStorage.getItem(TOKEN_KEY),
  loading: false,
  error: null,

  // Actions
  setToken: (token) => {
    if (token) {
      localStorage.setItem(TOKEN_KEY, token);
    } else {
      localStorage.removeItem(TOKEN_KEY);
    }
    set({ token, isAuthenticated: !!token });
  },

  setUser: (user) => {
    if (user) {
      localStorage.setItem(USER_KEY, JSON.stringify(user));
    } else {
      localStorage.removeItem(USER_KEY);
    }
    set({ user });
  },

  setLoading: (loading) => set({ loading }),
  setError: (error) => set({ error }),

  login: (token, user) => {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(USER_KEY, JSON.stringify(user));
    set({ token, user, isAuthenticated: true, error: null });
  },

  logout: () => {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(USER_KEY);
    set({ token: null, user: null, isAuthenticated: false, error: null });
  },

  clearError: () => set({ error: null }),

  // Check if token exists (for initial load)
  checkAuth: () => {
    const token = localStorage.getItem(TOKEN_KEY);
    const user = JSON.parse(localStorage.getItem(USER_KEY) || 'null');
    set({ token, user, isAuthenticated: !!token });
    return !!token;
  },
}));

export default useAuthStore;
