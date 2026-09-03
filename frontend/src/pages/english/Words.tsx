import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import './Words.css'

/** 单词功能占位页 */
export default function Words() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="words-page">
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

      <main className="words-main">
        <h1 className="words-title">单词</h1>
        <span className="words-accent" aria-hidden="true" />
        <p className="words-subtitle">智能背单词，艾宾浩斯复习</p>

        <div className="words-placeholder">
          <div className="words-icon" aria-hidden="true">🚀</div>
          <p className="words-placeholder-title">功能建设中，敬请期待</p>
          <p className="words-placeholder-sub">单词学习功能正在紧张开发中...</p>
        </div>
      </main>

      <button className="words-back" onClick={() => navigate(-1)}>
        ← 返回
      </button>
    </div>
  )
}
