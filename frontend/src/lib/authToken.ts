const TOKEN_KEY = 'nsd_auth_token'
const EVENT = 'nsd-auth-token-change'

export function getToken(): string | null {
  try {
    return localStorage.getItem(TOKEN_KEY)
  } catch {
    return null
  }
}

export function setToken(token: string) {
  try {
    localStorage.setItem(TOKEN_KEY, token)
  } catch {
    // Storage can fail in private/restricted browser contexts.
  }
  window.dispatchEvent(new CustomEvent(EVENT))
}

export function clearToken() {
  try {
    localStorage.removeItem(TOKEN_KEY)
  } catch {
    // Storage can fail in private/restricted browser contexts.
  }
  window.dispatchEvent(new CustomEvent(EVENT))
}

export function onTokenChange(handler: () => void) {
  window.addEventListener(EVENT, handler)
  window.addEventListener('storage', handler)
  return () => {
    window.removeEventListener(EVENT, handler)
    window.removeEventListener('storage', handler)
  }
}
