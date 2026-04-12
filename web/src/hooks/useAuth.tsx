import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'
import { useNavigate } from 'react-router-dom'
import { type User, getMe, login as apiLogin, register as apiRegister } from '@/api/auth'
import { ApiError } from '@/api/client'

interface AuthContextValue {
  user: User | null
  token: string | null
  isLoading: boolean
  error: string | null
  login: (email: string, password: string) => Promise<void>
  register: (email: string, password: string, name: string) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | null>(null)

const TOKEN_KEY = 'neura_token'

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [token, setToken] = useState<string | null>(() => localStorage.getItem(TOKEN_KEY))
  const [isLoading, setIsLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const navigate = useNavigate()

  // Restore session on mount
  useEffect(() => {
    const stored = localStorage.getItem(TOKEN_KEY)
    if (!stored) {
      setIsLoading(false)
      return
    }
    getMe()
      .then(({ user }) => {
        setUser(user)
        setToken(stored)
      })
      .catch(() => {
        localStorage.removeItem(TOKEN_KEY)
        setToken(null)
      })
      .finally(() => setIsLoading(false))
  }, [])

  const saveAuth = useCallback((tok: string, u: User) => {
    localStorage.setItem(TOKEN_KEY, tok)
    setToken(tok)
    setUser(u)
    setError(null)
  }, [])

  const login = useCallback(async (email: string, password: string) => {
    setError(null)
    try {
      const res = await apiLogin(email, password)
      saveAuth(res.token, res.user)
      navigate('/chat')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Ошибка входа'
      setError(msg)
      throw e
    }
  }, [saveAuth, navigate])

  const register = useCallback(async (email: string, password: string, name: string) => {
    setError(null)
    try {
      const res = await apiRegister(email, password, name)
      saveAuth(res.token, res.user)
      navigate('/chat')
    } catch (e) {
      const msg = e instanceof ApiError ? e.message : 'Ошибка регистрации'
      setError(msg)
      throw e
    }
  }, [saveAuth, navigate])

  const logout = useCallback(() => {
    sessionStorage.clear()
    localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
    navigate('/login')
  }, [navigate])

  const value = useMemo<AuthContextValue>(
    () => ({ user, token, isLoading, error, login, register, logout }),
    [user, token, isLoading, error, login, register, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth(): AuthContextValue {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth must be used within AuthProvider')
  return ctx
}
