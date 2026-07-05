/** Axios instanca s JWT interceptorom i automatskim refreshom tokena. */

import axios from 'axios';
import * as SecureStore from 'expo-secure-store';

// U Expo Go postavi EXPO_PUBLIC_API_URL na IP računala (npr. http://192.168.1.10)
export const API_URL = process.env.EXPO_PUBLIC_API_URL ?? 'http://localhost';

export const api = axios.create({ baseURL: API_URL, timeout: 15000 });

const ACCESS_KEY = 'access_token';
const REFRESH_KEY = 'refresh_token';

export async function saveTokens(access: string, refresh?: string) {
  await SecureStore.setItemAsync(ACCESS_KEY, access);
  if (refresh) await SecureStore.setItemAsync(REFRESH_KEY, refresh);
}

export async function clearTokens() {
  await SecureStore.deleteItemAsync(ACCESS_KEY);
  await SecureStore.deleteItemAsync(REFRESH_KEY);
}

export async function getAccessToken() {
  return SecureStore.getItemAsync(ACCESS_KEY);
}

api.interceptors.request.use(async (config) => {
  const token = await getAccessToken();
  if (token) config.headers.Authorization = `Bearer ${token}`;
  return config;
});

let refreshing: Promise<string | null> | null = null;

async function refreshAccessToken(): Promise<string | null> {
  const refresh = await SecureStore.getItemAsync(REFRESH_KEY);
  if (!refresh) return null;
  try {
    const res = await axios.post(`${API_URL}/api/auth/refresh`, null, {
      headers: { Authorization: `Bearer ${refresh}` },
    });
    await saveTokens(res.data.access_token, res.data.refresh_token);
    return res.data.access_token;
  } catch {
    await clearTokens();
    return null;
  }
}

api.interceptors.response.use(
  (res) => res,
  async (error) => {
    const original = error.config;
    if (error.response?.status === 401 && !original._retried) {
      original._retried = true;
      refreshing = refreshing ?? refreshAccessToken();
      const token = await refreshing;
      refreshing = null;
      if (token) {
        original.headers.Authorization = `Bearer ${token}`;
        return api(original);
      }
    }
    return Promise.reject(error);
  },
);

export function errorMessage(err: any): string {
  return err?.response?.data?.error ?? err?.message ?? 'Nešto je pošlo po zlu';
}
