import { createContext, useCallback, useContext, useMemo, useState } from 'react'
import { loginFarmer, loginUser, registerUser } from '../api'
import { errorMessage } from '../utils/formatError'

const SESSION_KEY = 'krishivoice_session'

function readSession() {
  try {
    const raw = localStorage.getItem(SESSION_KEY)
    return raw ? JSON.parse(raw) : null
  } catch {
    return null
  }
}

const AuthContext = createContext(null)

export function AuthProvider({ children }) {
  const [session, setSession] = useState(readSession)
  const [authError, setAuthError] = useState(null)
  const [loggingIn, setLoggingIn] = useState(false)

  const saveSession = useCallback((result, authMode) => {
    const next = {
      farmerId: result.farmer_id,
      parcelId: result.parcel_id || null,
      district: result.district || null,
      village: result.village || null,
      token: result.token,
      displayName: result.display_name,
      userId: result.user_id || null,
      username: result.username || null,
      authMode,
    }
    localStorage.setItem(SESSION_KEY, JSON.stringify(next))
    setSession(next)
    return result
  }, [])

  const login = useCallback(async (farmerId, pin) => {
    setAuthError(null)
    setLoggingIn(true)
    try {
      const result = await loginFarmer(farmerId.trim().toUpperCase(), pin)
      return saveSession(result, result.auth_mode || 'farmer')
    } catch (e) {
      setAuthError(errorMessage(e, 'Login failed. Check your credentials.'))
      throw e
    } finally {
      setLoggingIn(false)
    }
  }, [saveSession])

  const loginWithUser = useCallback(async (username, password) => {
    setAuthError(null)
    setLoggingIn(true)
    try {
      const result = await loginUser(username.trim(), password)
      return saveSession(result, 'user')
    } catch (e) {
      setAuthError(errorMessage(e, 'Login failed. Check your credentials.'))
      throw e
    } finally {
      setLoggingIn(false)
    }
  }, [saveSession])

  const register = useCallback(async ({ username, password, displayName, farmerId, district, village, primaryCrop }) => {
    setAuthError(null)
    setLoggingIn(true)
    try {
      const result = await registerUser({ username, password, displayName, farmerId, district, village, primaryCrop })
      return saveSession(result, 'user')
    } catch (e) {
      setAuthError(errorMessage(e, 'Registration failed. Please try again.'))
      throw e
    } finally {
      setLoggingIn(false)
    }
  }, [saveSession])

  const logout = useCallback(() => {
    localStorage.removeItem(SESSION_KEY)
    setSession(null)
    setAuthError(null)
  }, [])

  const value = useMemo(
    () => ({
      session,
      isGuest: !session,
      farmerId: session?.farmerId ?? null,
      parcelId: session?.parcelId ?? null,
      district: session?.district ?? null,
      village: session?.village ?? null,
      userId: session?.userId ?? null,
      username: session?.username ?? null,
      authMode: session?.authMode ?? null,
      isUserAuth: session?.authMode === 'user',
      displayName: session?.displayName ?? null,
      token: session?.token ?? null,
      login,
      loginWithUser,
      register,
      logout,
      authError,
      loggingIn,
      clearAuthError: () => setAuthError(null),
    }),
    [session, login, loginWithUser, register, logout, authError, loggingIn],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
