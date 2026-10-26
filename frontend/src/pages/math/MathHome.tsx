import { useState } from 'react'
import { NavLink, Outlet, useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import { CHAPTERS, SUB_ITEMS } from './chapters'
import './MathHome.css'

/**
 * 数学模块外壳：顶部导航 + 章节树左侧导航，右侧内容由嵌套路由渲染。
 * 与英语模块（EnglishHome）保持一致的布局与配色，仅管理员可访问（路由已加守卫）。
 */
export default function MathHome() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  // 默认展开「一、极限」
  const [expanded, setExpanded] = useState<Record<string, boolean>>({ limit: true })

  const toggle = (id: string) => setExpanded((e) => ({ ...e, [id]: !e[id] }))

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
        {/* 左侧章节导航 */}
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
            <div className="math-menu-caption">📚 高等数学</div>

            {CHAPTERS.map((chapter) => {
              const isOpen = expanded[chapter.id] === true
              return (
                <div className="math-chapter" key={chapter.id}>
                  <button
                    className="math-chapter-head"
                    onClick={() => toggle(chapter.id)}
                    aria-expanded={isOpen}
                  >
                    <span className="math-chapter-arrow" aria-hidden="true">
                      {isOpen ? '▾' : '▸'}
                    </span>
                    <span className="math-chapter-name">{chapter.label}</span>
                  </button>

                  {isOpen && (
                    <div className="math-chapter-items">
                      {SUB_ITEMS.map((sub) => (
                        <NavLink
                          key={sub.id}
                          to={`/math/${chapter.id}/${sub.id}`}
                          className={({ isActive }) =>
                            isActive
                              ? 'math-menu-item math-menu-item-active math-subitem'
                              : 'math-menu-item math-subitem'
                          }
                        >
                          <span className="math-menu-icon">{sub.icon}</span>
                          <span>{sub.label}</span>
                        </NavLink>
                      ))}
                    </div>
                  )}
                </div>
              )
            })}
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
