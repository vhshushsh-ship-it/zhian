import { CHAPTERS } from './chapters'
import './ComingSoon.css'

/** 未开放章节的统一占位页 */
export default function ComingSoon({ chapterId }: { chapterId?: string }) {
  const chapter = CHAPTERS.find((c) => c.id === chapterId)
  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">内容整理中</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">
          {chapter ? `${chapter.label} · 内容正在整理，敬请期待` : '内容正在整理，敬请期待'}
        </p>
      </header>

      <div className="coming-soon-card">
        <span className="coming-soon-emoji" aria-hidden="true">
          📚
        </span>
        <p className="coming-soon-text">内容整理中…</p>
      </div>
    </div>
  )
}
