import { NavLink, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Navbar from '../components/Navbar'
import './EnglishHome.css'

interface NavItem {
  id: string
  label: string
  icon: string
  path: string
}

const NAV_ITEMS: NavItem[] = [
  { id: 'words', label: '单词', icon: '📖', path: '/english/words' },
  { id: 'speaking', label: '口语练习', icon: '🎤', path: '/english/speaking' },
  { id: 'reading', label: '外刊精读', icon: '🔍', path: '/english/reading' },
  { id: 'stats', label: '学习数据', icon: '📊', path: '/english/stats' },
]

/**
 * 英语模块外壳：顶部导航 + 左侧功能导航，右侧内容由嵌套路由渲染。
 * 左侧导航改用 URL 驱动（NavLink 高亮 + navigate），使浏览器历史能记录子页面切换，
 * 顶部「返回上一页」可正确回到英语模块内的上一个页面。
 */
export default function EnglishHome() {
  const { user, logout } = useAuth()
  const location = useLocation()

  // 单词 / 口语是应用式满高布局（含介绍页与主界面），内容区需去掉内边距、自身滚动
  const isFullBleed =
    location.pathname.startsWith('/english/words') ||
    location.pathname.startsWith('/english/speaking')

  // 全屏页面：隐藏左侧导航，内容占满整个屏幕宽度（主界面 / 文章列表 / 文章详情）
  const hideSidebar =
    location.pathname === '/english/words/practice' ||
    location.pathname === '/english/speaking/practice' ||
    location.pathname === '/english/reading/list' ||
    /^\/english\/reading\/\d+$/.test(location.pathname)

  return (
    <div className="english-page">
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

      <div className="english-layout">
        {/* 左侧导航（全屏页面隐藏） */}
        {!hideSidebar && (
          <aside className="english-sidebar">
            <div className="english-sidebar-title">
              <h1>英语</h1>
              <p>English Learning</p>
              <span className="english-sidebar-accent" aria-hidden="true" />
            </div>

            <nav className="english-menu">
              {NAV_ITEMS.map((item) => (
                <NavLink
                  key={item.id}
                  to={item.path}
                  className={({ isActive }) =>
                    isActive
                      ? 'english-menu-item english-menu-item-active'
                      : 'english-menu-item'
                  }
                >
                  <span className="english-menu-icon">{item.icon}</span>
                  <span>{item.label}</span>
                </NavLink>
              ))}
            </nav>
          </aside>
        )}

        {/* 右侧内容 */}
        <main
          className={
            isFullBleed ? 'english-content english-content-fill' : 'english-content'
          }
        >
          <Outlet />
        </main>
      </div>
    </div>
  )
}
