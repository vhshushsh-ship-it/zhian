import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import './MathHome.css'

interface NavItem {
  id: string
  label: string
  icon: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'overview', label: '数学概览', icon: '📐', path: '/math/overview' },
  { id: 'methods', label: '题型方法', icon: '🧮', path: '/math/methods' },
  { id: 'examples', label: '例题精讲', icon: '📝', path: '/math/examples' },
]

/**
 * 数学模块外壳：顶部导航 + 左侧功能导航，右侧内容由嵌套路由渲染。
 * 与英语模块（EnglishHome）保持一致的布局与配色，仅管理员可访问（路由已加守卫）。
 */
export default function MathHome() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="math-page">
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

      <div className="math-layout">
        {/* 左侧导航 */}
        <aside className="math-sidebar">
          <div className="math-sidebar-title">
            <button className="math-back" onClick={() => navigate('/dashboard')}>
              ← 返回仪表盘
            </button>
            <h1>数学</h1>
            <p>Mathematics</p>
            <span className="math-sidebar-accent" aria-hidden="true" />
          </div>

          <nav className="math-menu">
            {NAV_ITEMS.map((item) => (
              <NavLink
                key={item.id}
                to={item.path}
                className={({ isActive }) =>
                  isActive ? 'math-menu-item math-menu-item-active' : 'math-menu-item'
                }
              >
                <span className="math-menu-icon">{item.icon}</span>
                <span>{item.label}</span>
              </NavLink>
            ))}
          </nav>
        </aside>

        {/* 右侧内容 */}
        <main className="math-content-area">
          <Outlet />
        </main>
      </div>
    </div>
  )
}
