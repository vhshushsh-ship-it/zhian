import type { ReactNode } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import './Navbar.css'

interface NavbarProps {
  /** 当前高亮的导航项 */
  active?: 'home' | 'features' | 'about' | 'admin'
  /** 右侧尾部内容（登录按钮，或用户邮箱 + 退出登录） */
  trailing?: ReactNode
}

/**
 * 全站通用顶部导航栏：logo「知岸」+ 返回上一页/功能/关于 + 可选尾部内容。
 * 欢迎页、登录注册页、Dashboard、学科页、管理后台共用。
 * 「管理后台」菜单仅管理员可见。
 */
export default function Navbar({ active, trailing }: NavbarProps) {
  const { user } = useAuth()
  const navigate = useNavigate()

  /** 返回浏览器上一页；无历史记录时回退到学习首页 */
  const goBack = () => {
    if (window.history.length > 1) {
      window.history.back()
    } else {
      navigate('/dashboard')
    }
  }

  return (
    <header className="navbar">
      <div className="navbar-left">
        <Link to="/" className="navbar-logo">知岸</Link>
        <button
          className="navbar-back"
          onClick={goBack}
          title="返回上一页"
          aria-label="返回上一页"
        >
          ←
        </button>
      </div>
      <div className="navbar-right">
        <Link
          to="/dashboard"
          className={active === 'home' ? 'navbar-active' : undefined}
        >
          首页
        </Link>
        <a
          href="#features"
          className={active === 'features' ? 'navbar-active' : undefined}
        >
          功能
        </a>
        <a href="#about" className={active === 'about' ? 'navbar-active' : undefined}>
          关于
        </a>
        {user?.role === 'admin' && (
          <Link
            to="/admin"
            className={active === 'admin' ? 'navbar-active' : undefined}
          >
            管理后台
          </Link>
        )}
        {trailing}
      </div>
    </header>
  )
}
