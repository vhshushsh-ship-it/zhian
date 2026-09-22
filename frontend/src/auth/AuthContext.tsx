import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { login as apiLogin, register as apiRegister } from '../api/auth'
import api from '../api/client'
import type { User } from '../types'

interface AuthContextValue {
  user: User | null
  loading: boolean
  demoMode: boolean
  skipDashboard: boolean
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
  const [demoMode, setDemoMode] = useState(false)
  const [skipDashboard, setSkipDashboard] = useState(false)
  const [loading, setLoading] = useState(true)

  // 应用启动时：先拉取演示模式开关，再按需加载当前用户信息
  useEffect(() => {
    ;(async () => {
      // 1. 拉取演示模式与跳过科目选择页开关（无需登录）
      let demo = false
      let skipDashboard = false
      try {
        const cfg = await api.get<{ demo_mode: boolean; skip_dashboard: boolean }>('/config')
        demo = !!cfg.data.demo_mode
        skipDashboard = !!cfg.data.skip_dashboard
      } catch {
        demo = false
        skipDashboard = false
      }
      setDemoMode(demo)
      setSkipDashboard(skipDashboard)

      if (demo) {
        // 演示模式：免登录，清掉可能残留的 token（后端自动识别演示用户）
        localStorage.removeItem('token')
      } else {
        // 正常模式：存在 token 则拉取当前用户信息
        const token = localStorage.getItem('token')
        if (token) {
          try {
            const res = await api.get<User>('/auth/me')
            setUser(res.data)
          } catch {
            localStorage.removeItem('token')
          }
        }
      }
      setLoading(false)
    })()
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
    <AuthContext.Provider value={{ user, loading, demoMode, skipDashboard, login, register, logout }}>
      {children}
    </AuthContext.Provider>
  )
}

export function useAuth() {
  const ctx = useContext(AuthContext)
  if (!ctx) throw new Error('useAuth 必须在 AuthProvider 内使用')
  return ctx
}
