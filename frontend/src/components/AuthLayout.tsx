import type { ReactNode } from 'react'
import { Link } from 'react-router-dom'
import './AuthLayout.css'

interface AuthLayoutProps {
  cardTitle: string
  brandTitle: string
  brandSubtitle: string
  children: ReactNode
  switchLink: ReactNode
}

/**
 * 登录 / 注册页共享布局：顶部导航 + 左右分栏（表单卡片 + 品牌展示）+ 底部横幅。
 * 与欢迎页 Welcome.tsx 的视觉风格保持一致。
 */
export default function AuthLayout({
  cardTitle,
  brandTitle,
  brandSubtitle,
  children,
  switchLink,
}: AuthLayoutProps) {
  return (
    <div className="auth-page">
      {/* 顶部导航 */}
      <header className="auth-nav">
        <Link to="/" className="auth-logo">知岸</Link>
        <nav className="auth-nav-links">
          <Link to="/" className="auth-nav-active">首页</Link>
          <a href="#features">功能</a>
          <a href="#about">关于</a>
        </nav>
      </header>

      {/* 主体：左右分栏 */}
      <main className="auth-main">
        {/* 左侧表单卡片 */}
        <div className="auth-card">
          <h1 className="auth-card-title">{cardTitle}</h1>
          <span className="auth-card-accent" aria-hidden="true" />
          {children}
          <div className="auth-switch">{switchLink}</div>
        </div>

        {/* 右侧品牌展示区 */}
        <div className="auth-brand">
          <h2 className="auth-brand-title">{brandTitle}</h2>
          <p className="auth-brand-subtitle">{brandSubtitle}</p>
          {/* AI 学习插画（CSS 绘制，不用外部图片） */}
          <div className="auth-illustration" aria-hidden="true">
            <div className="auth-bubble auth-bubble-user">今天学点什么？</div>
            <div className="auth-bubble auth-bubble-bot">已为你规划好今日学习路径</div>
            <div className="auth-chip">AI 学习助手</div>
          </div>
          {/* 装饰几何色块 */}
          <div className="auth-deco auth-deco-red" aria-hidden="true" />
          <div className="auth-deco auth-deco-yellow" aria-hidden="true" />
        </div>
      </main>

      {/* 底部横幅 */}
      <footer className="auth-footer">
        <p>全新的 AI 学习体验，助力每一位学习者高效上岸</p>
      </footer>
    </div>
  )
}
