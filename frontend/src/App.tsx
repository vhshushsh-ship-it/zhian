import { type ReactElement } from 'react'
import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from './auth/AuthContext'
import Admin from './pages/Admin'
import Dashboard from './pages/Dashboard'
import Login from './pages/Login'
import Register from './pages/Register'
import Subject from './pages/Subject'
import Welcome from './pages/Welcome'

function Protected({ children }: { children: ReactElement }) {
  const { user, loading } = useAuth()
  if (loading) return <div className="center">加载中…</div>
  if (!user) return <Navigate to="/login" replace />
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
    <Routes>
      <Route path="/" element={<Welcome />} />
      <Route path="/login" element={<Login />} />
      <Route path="/register" element={<Register />} />
      <Route
        path="/dashboard"
        element={
          <Protected>
            <Dashboard />
          </Protected>
        }
      />
      <Route
        path="/subject/:id"
        element={
          <Protected>
            <Subject />
          </Protected>
        }
      />
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
  )
}
