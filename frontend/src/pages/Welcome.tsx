import { useNavigate } from 'react-router-dom'
import './Welcome.css'

export default function Welcome() {
  const navigate = useNavigate()

  return (
    <div className="welcome">
      {/* 顶部导航 */}
      <header className="welcome-nav">
        <div className="welcome-logo">知岸</div>
        <nav className="welcome-nav-links">
          <a href="#home">首页</a>
          <a href="#features">功能</a>
          <a href="#about">关于</a>
          <button className="welcome-nav-login" onClick={() => navigate('/login')}>
            登录
          </button>
        </nav>
      </header>

      {/* 主内容：左右分栏 */}
      <main className="welcome-hero" id="home">
        {/* 左侧文字内容 */}
        <div className="welcome-left">
          <h1 className="welcome-title">知岸</h1>
          <p className="welcome-subtitle">AI 加持，让每一次学习都更加高效</p>
          <button className="welcome-cta" onClick={() => navigate('/login')}>
            使用网页版
          </button>
        </div>

        {/* 右侧产品展示图：笔记本电脑 mockup（CSS 绘制） */}
        <div className="welcome-right">
          <div className="laptop">
            <div className="laptop-screen">
              {/* 屏幕内 AI 学习界面示意图 */}
              <div className="ai-ui">
                <div className="ai-chat">
                  <div className="ai-bubble ai-bubble-user">帮我总结一下今天的知识点</div>
                  <div className="ai-bubble ai-bubble-bot">好的，已为你生成学习卡片…</div>
                </div>
                <div className="ai-cards">
                  <div className="ai-card">
                    <div className="ai-card-title">知识点 1</div>
                    <div className="ai-card-line" />
                    <div className="ai-card-line short" />
                  </div>
                  <div className="ai-card">
                    <div className="ai-card-title">知识点 2</div>
                    <div className="ai-card-line" />
                    <div className="ai-card-line short" />
                  </div>
                </div>
              </div>
            </div>
            <div className="laptop-base" />
          </div>
        </div>

        {/* 装饰几何色块（CSS 绘制，不用外部图片） */}
        <div className="deco deco-red" aria-hidden="true" />
        <div className="deco deco-yellow" aria-hidden="true" />
      </main>

      {/* 底部横幅 */}
      <footer className="welcome-footer" id="about">
        <p>全新的 AI 学习体验，助力每一位学习者高效上岸</p>
      </footer>
    </div>
  )
}
