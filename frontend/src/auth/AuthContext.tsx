import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as apiLogin, register as apiRegister } from '../api/auth'
import api from '../api/client'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  login: (email: string, password: string) => Promise<void>
  register: (
    email: string,
    code: string,
    password: string,
    confirmPassword: string,
  ) => Promise<void>
  logout: () => void
}

const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const navigate = useNavigate()
  const [user, setUser] = useState<User | null>(null)
  const [loading, setLoading] = useState(true)

  // 应用启动时，若存在 token 则拉取当前用户信息
  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      setLoading(false)
      return
    }
    api
      .get<User>('/auth/me')
      .then((res) => setUser(res.data))
      .catch(() => localStorage.removeItem('token'))
      .finally(() => setLoading(false))
  }, [])

  const login = async (email: string, password: string) => {
    const res = await apiLogin(email, password)
    localStorage.setItem('token', res.data.access_token)
    setUser(res.data.user)
    // 按角色跳转：管理员进后台，普通用户进学科选择
    navigate(res.data.user.role === 'admin' ? '/admin' : '/dashboard')
  }

  const register = async (
    email: string,
    code: string,
    password: string,
    confirmPassword: string,
  ) => {
    const res = await apiRegister(email, code, password, confirmPassword)
    localStorage.setItem('token', res.data.access_token)
    setUser(res.data.user)
    // 注册的都是普通用户
    navigate('/dashboard')
  }

  const logout = () => {
    localStorage.removeItem('token')
    setUser(null)
    navigate('/')
  }

  return (
    <AuthContext.Provider value={{ user, loading, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return ctx
}
