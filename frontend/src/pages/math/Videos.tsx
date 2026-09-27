import './Videos.css'

interface VideoItem {
  id: string
  title: string
  desc: string
  url?: string
}

const CHAPTER_ONE: VideoItem[] = [
  {
    id: 'sequence-limit',
    title: '数列极限',
    desc: 'B站免费课程，系统讲解数列极限的概念和求法',
    url: 'https://www.bilibili.com/video/BV1fpxLeYEmX/',
  },
]

/** 视频讲解：B 站免费课程卡片（内容先静态写死，后续接入数据库） */
export default function Videos() {
  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">视频讲解</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">跟着 B 站免费课程学习</p>
      </header>

      <section className="video-section">
        <h3 className="video-chapter">第一章：函数与极限</h3>

        {CHAPTER_ONE.map((v) => (
          <div key={v.id} className="video-card">
            <div className="video-card-body">
              <h4 className="video-title">{v.title}</h4>
              <p className="video-desc">{v.desc}</p>
            </div>
            {v.url && (
              <a
                className="video-btn"
                href={v.url}
                target="_blank"
                rel="noopener noreferrer"
              >
                ▶ 观看视频
              </a>
            )}
          </div>
        ))}

        <div className="video-placeholder">
          <p className="video-placeholder-text">更多视频即将上线</p>
        </div>
      </section>
    </div>
  )
}
