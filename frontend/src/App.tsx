import { type ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import AiTutor from './components/AiTutor'
import Admin from './pages/Admin'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Subject from './pages/Subject'
import Welcome from './pages/Welcome'
import EnglishHome from './pages/EnglishHome'
import { ReadingContent } from './pages/english/Reading'
import Speaking from './pages/english/Speaking'
import { StatsContent } from './pages/english/Stats'
import Words from './pages/english/Words'

function Protected({ children }: { children: ReactElement }) {
  const { user, loading, demoMode } = useAuth()
  if (loading) return <div className="center">加载中…</div>
  // 演示模式：免登录直接放行
  if (demoMode) return children
  if (!user) return <Navigate to="/login" replace />
  return children
}

/** 比赛期间跳过科目选择页：访问 /dashboard 时重定向到英语学习页 */
function DashboardGate({ children }: { children: ReactElement }) {
  const { user, skipDashboard } = useAuth()
  if (skipDashboard) return <Navigate to="/english" replace />
  // 普通用户（非管理员）不经过仪表盘，直接进英语学习
  if (user && user.role !== 'admin') return <Navigate to="/english" replace />
  return children
}

/** 数学 / 计算机网络占位页：仅管理员可访问，普通用户重定向到英语学习页 */
function SubjectGate({ children }: { children: ReactElement }) {
  const { user } = useAuth()
  if (user && user.role !== 'admin') return <Navigate to="/english" replace />
  return children
}

/** 仅管理员可访问的路由 */
function AdminRoute({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center">加载中…</div>
  if (!user) return <Navigate to="/login" replace />
  if (user.role !== 'admin') return <Navigate to="/dashboard" replace />
  return children
}

export default function App() {
  return (
    <>
      <Routes>
        <Route path="/" element={<Welcome />} />
        <Route path="/login" element={<Login />} />
        <Route path="/register" element={<Register />} />
        <Route
          path="/dashboard"
          element={
            <Protected>
              <DashboardGate>
                <Dashboard />
              </DashboardGate>
            </Protected>
          }
        />
        <Route
          path="/subject/:id"
          element={
            <Protected>
              <SubjectGate>
                <Subject />
              </SubjectGate>
            </Protected>
          }
        />
        {/* 数学 / 计算机网络占位页的短路径别名（普通用户直接访问会重定向到英语学习页） */}
        <Route path="/math" element={<Navigate to="/subject/math" replace />} />
        <Route path="/cs" element={<Navigate to="/subject/cs" replace />} />
        <Route
          path="/english"
          element={
            <Protected>
              <EnglishHome />
            </Protected>
          }
        >
          <Route index element={<Navigate to="/english/speaking" replace />} />
          <Route path="words/*" element={<Words />} />
          <Route path="speaking/*" element={<Speaking />} />
          <Route path="reading/*" element={<ReadingContent />} />
          <Route path="stats" element={<StatsContent />} />
        </Route>
        <Route
          path="/admin"
          element={
            <AdminRoute>
              <Admin />
            </AdminRoute>
          }
        />
        <Route path="*" element={<Navigate to="/" replace />} />
      </Routes>
      <AiTutor />
    </>
  )
}
