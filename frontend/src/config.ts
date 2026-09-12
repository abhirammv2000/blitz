export const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8001'

const ACCESS_KEY_STORAGE_KEY = 'blitz_access_key'

// localStorage can throw (private browsing, disabled site data) or just not
// be there - a missing key means the header goes out empty, which is exactly
// what a backend with no ACCESS_KEY configured expects anyway.
export function getAccessKey(): string {
  try {
    return localStorage.getItem(ACCESS_KEY_STORAGE_KEY) ?? ''
  } catch {
    return ''
  }
}

export function setAccessKey(key: string): void {
  try {
    localStorage.setItem(ACCESS_KEY_STORAGE_KEY, key)
  } catch {
    // Not fatal - the key just won't survive a reload.
  }
}

// Every call to the backend should go through this instead of bare fetch, so
// the access key header is never forgotten at a new call site. Sending it
// when the backend has no ACCESS_KEY configured is harmless - nothing checks it.
export function apiFetch(path: string, init: RequestInit = {}): Promise<Response> {
  const headers = new Headers(init.headers)
  const key = getAccessKey()
  if (key) headers.set('X-Blitz-Key', key)
  return fetch(`${API_BASE}${path}`, { ...init, headers })
}
