/** Zustand store — autentikacija, košarica pića, kontekst rezervacije. */

import { create } from 'zustand';
import { api, clearTokens, errorMessage, saveTokens } from '../services/api';

type User = {
  _id: string;
  email: string;
  name: string;
  phone?: string;
  profile_image?: string | null;
};

type Staff = { _id: string; name: string; club_id: string };

type AuthState = {
  user: User | null;
  staff: Staff | null;
  role: 'user' | 'hostess' | 'waiter' | null;
  loading: boolean;
  login: (email: string, password: string) => Promise<void>;
  register: (name: string, email: string, password: string, phone?: string) => Promise<void>;
  oauthLogin: (provider: 'google' | 'facebook', token: string) => Promise<void>;
  staffLogin: (email: string, pin: string) => Promise<void>;
  logout: () => Promise<void>;
};

export const useAuthStore = create<AuthState>((set) => ({
  user: null,
  staff: null,
  role: null,
  loading: false,

  login: async (email, password) => {
    set({ loading: true });
    try {
      const res = await api.post('/api/auth/login', { email, password });
      await saveTokens(res.data.access_token, res.data.refresh_token);
      set({ user: res.data.user, role: 'user', staff: null });
    } catch (err) {
      throw new Error(errorMessage(err));
    } finally {
      set({ loading: false });
    }
  },

  register: async (name, email, password, phone) => {
    set({ loading: true });
    try {
      const res = await api.post('/api/auth/register', { name, email, password, phone });
      await saveTokens(res.data.access_token, res.data.refresh_token);
      set({ user: res.data.user, role: 'user', staff: null });
    } catch (err) {
      throw new Error(errorMessage(err));
    } finally {
      set({ loading: false });
    }
  },

  oauthLogin: async (provider, token) => {
    set({ loading: true });
    try {
      const body = provider === 'google' ? { id_token: token } : { access_token: token };
      const res = await api.post(`/api/auth/${provider}`, body);
      await saveTokens(res.data.access_token, res.data.refresh_token);
      set({ user: res.data.user, role: 'user', staff: null });
    } catch (err) {
      throw new Error(errorMessage(err));
    } finally {
      set({ loading: false });
    }
  },

  staffLogin: async (email, pin) => {
    set({ loading: true });
    try {
      const res = await api.post('/api/auth/staff/login', { email, pin });
      await saveTokens(res.data.access_token, res.data.refresh_token);
      set({ staff: res.data.staff, role: res.data.role, user: null });
    } catch (err) {
      throw new Error(errorMessage(err));
    } finally {
      set({ loading: false });
    }
  },

  logout: async () => {
    await clearTokens();
    set({ user: null, staff: null, role: null });
  },
}));

// ---------- Košarica pića ----------

export type CartItem = {
  menu_item_id: string;
  name: string;
  price: number;
  quantity: number;
};

type CartState = {
  reservationId: string | null;
  eventId: string | null;
  clubId: string | null;
  items: CartItem[];
  setContext: (reservationId: string, eventId: string, clubId: string) => void;
  add: (item: Omit<CartItem, 'quantity'>) => void;
  remove: (menuItemId: string) => void;
  setQuantity: (menuItemId: string, quantity: number) => void;
  clear: () => void;
  total: () => number;
};

export const useCartStore = create<CartState>((set, get) => ({
  reservationId: null,
  eventId: null,
  clubId: null,
  items: [],

  setContext: (reservationId, eventId, clubId) =>
    set({ reservationId, eventId, clubId }),

  add: (item) =>
    set((s) => {
      const existing = s.items.find((i) => i.menu_item_id === item.menu_item_id);
      if (existing) {
        return {
          items: s.items.map((i) =>
            i.menu_item_id === item.menu_item_id ? { ...i, quantity: i.quantity + 1 } : i),
        };
      }
      return { items: [...s.items, { ...item, quantity: 1 }] };
    }),

  remove: (menuItemId) =>
    set((s) => ({ items: s.items.filter((i) => i.menu_item_id !== menuItemId) })),

  setQuantity: (menuItemId, quantity) =>
    set((s) => ({
      items: quantity < 1
        ? s.items.filter((i) => i.menu_item_id !== menuItemId)
        : s.items.map((i) => (i.menu_item_id === menuItemId ? { ...i, quantity } : i)),
    })),

  clear: () => set({ items: [] }),

  total: () => get().items.reduce((sum, i) => sum + i.price * i.quantity, 0),
}));
