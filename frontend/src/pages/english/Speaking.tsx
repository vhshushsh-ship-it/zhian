import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import './Speaking.css'

/** 口语练习功能占位页 */
export default function Speaking() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="speaking-page">
      <Navbar
        active="home"
        trailing={
          <>
            <span className="navbar-email">{user?.email || user?.username}</span>
            <button className="navbar-btn" onClick={logout}>
              退出登录
            </button>
          </>
        }
      />

      <main className="speaking-main">
        <h1 className="speaking-title">口语练习</h1>
        <span className="speaking-accent" aria-hidden="true" />
        <p className="speaking-subtitle">AI 对话练习，实时发音评分</p>

        <div className="speaking-placeholder">
          <div className="speaking-icon" aria-hidden="true">🚀</div>
          <p className="speaking-placeholder-title">功能建设中，敬请期待</p>
          <p className="speaking-placeholder-sub">口语练习功能正在紧张开发中...</p>
        </div>
      </main>

      <button className="speaking-back" onClick={() => navigate(-1)}>
        ← 返回
      </button>
    </div>
  )
}
