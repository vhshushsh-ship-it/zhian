import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import './Reading.css'

/** 阅读练习功能占位页 */
export default function Reading() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="reading-page">
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

      <main className="reading-main">
        <h1 className="reading-title">阅读练习</h1>
        <span className="reading-accent" aria-hidden="true" />
        <p className="reading-subtitle">精选文章阅读，长难句解析</p>

        <div className="reading-placeholder">
          <div className="reading-icon" aria-hidden="true">🚀</div>
          <p className="reading-placeholder-title">功能建设中，敬请期待</p>
          <p className="reading-placeholder-sub">阅读练习功能正在紧张开发中...</p>
        </div>
      </main>

      <button className="reading-back" onClick={() => navigate(-1)}>
        ← 返回
      </button>
    </div>
  )
}
