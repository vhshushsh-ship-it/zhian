import { useNavigate } from 'react-router-dom'
import './Overview.css'

interface Chapter {
  id: string
  name: string
  chapter: string
  icon: string
  theme: 'red' | 'yellow' | 'blue'
}

const CHAPTERS: Chapter[] = [
  { id: 'limit', name: '函数与极限', chapter: '第一章', icon: '📐', theme: 'red' },
  { id: 'derivative', name: '导数与微分', chapter: '第二章', icon: '🧮', theme: 'yellow' },
  { id: 'integral', name: '积分', chapter: '第三章', icon: '📊', theme: 'blue' },
]

/** 数学概览：三章入口卡片（点击暂跳转到题型方法页） */
export default function Overview() {
  const navigate = useNavigate()

  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">高等数学</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">AI 辅助，系统掌握高数核心方法</p>
      </header>

      <div className="overview-grid">
        {CHAPTERS.map((c) => (
          <div
            key={c.id}
            className="chapter-card"
            onClick={() => navigate('/math/methods')}
            title={`进入「${c.name}」`}
          >
            <div className={`chapter-icon chapter-icon-${c.theme}`}>{c.icon}</div>
            <span className="chapter-tag">{c.chapter}</span>
            <h3 className="chapter-name">{c.name}</h3>
          </div>
        ))}
      </div>
    </div>
  )
}
