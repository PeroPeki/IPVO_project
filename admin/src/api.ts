/** Fetch wrapper s JWT tokenom i club_id kontekstom za superadmina. */

const TOKEN_KEY = 'admin_token';
const ROLE_KEY = 'admin_role';
const CLUB_KEY = 'admin_club_id';

export const auth = {
  get token() { return localStorage.getItem(TOKEN_KEY); },
  get role() { return localStorage.getItem(ROLE_KEY); },
  get clubId() { return localStorage.getItem(CLUB_KEY); },
  login(token: string, role: string) {
    localStorage.setItem(TOKEN_KEY, token);
    localStorage.setItem(ROLE_KEY, role);
  },
  setClub(clubId: string) { localStorage.setItem(CLUB_KEY, clubId); },
  logout() {
    localStorage.removeItem(TOKEN_KEY);
    localStorage.removeItem(ROLE_KEY);
    localStorage.removeItem(CLUB_KEY);
  },
};

/** club_id iz JWT claimova (club admin) ili iz superadminova odabira. */
export function effectiveClubId(): string | null {
  if (auth.role === 'superadmin') return auth.clubId;
  try {
    const payload = JSON.parse(atob((auth.token || '').split('.')[1]));
    return payload.club_id ?? null;
  } catch {
    return null;
  }
}

/** Superadmin nema club claim pa admin rute dobivaju ?club_id= iz odabira. */
function withClubParam(path: string): string {
  if (auth.role !== 'superadmin' || !auth.clubId) return path;
  const needsClub = path.startsWith('/api/admin')
    || path === '/api/events' || path === '/api/floor-maps' || path === '/api/menu';
  if (!needsClub) return path;
  return path + (path.includes('?') ? '&' : '?') + `club_id=${auth.clubId}`;
}

export async function api<T = any>(
  path: string,
  options: { method?: string; body?: any; formData?: FormData } = {},
): Promise<T> {
  const headers: Record<string, string> = {};
  if (auth.token) headers['Authorization'] = `Bearer ${auth.token}`;
  if (options.body) headers['Content-Type'] = 'application/json';

  const res = await fetch(withClubParam(path), {
    method: options.method || (options.body || options.formData ? 'POST' : 'GET'),
    headers,
    body: options.formData ?? (options.body ? JSON.stringify(options.body) : undefined),
  });

  if (res.status === 401) {
    auth.logout();
    window.location.href = '/login';
    throw new Error('Sesija je istekla');
  }

  const data = await res.json().catch(() => ({}));
  if (!res.ok) throw new Error(data.error || `Greška ${res.status}`);
  return data as T;
}
