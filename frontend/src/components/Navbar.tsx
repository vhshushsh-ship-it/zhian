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
  return (
    <header className="navbar">
      <Link to="/" className="navbar-logo">知岸</Link>
      <div className="navbar-right">
        <button className="navbar-back" onClick={() => navigate(-1)}>
          ← 返回上一页
        </button>
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
