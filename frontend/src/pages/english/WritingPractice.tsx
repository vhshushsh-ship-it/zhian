import { useEffect, useState } from 'react'
import { useAuth } from '../../auth/AuthContext'
import { getErrorMessage } from '../../api/client'
import {
  generateTopics,
  getWritingDetail,
  getWritingHistory,
  getWritingTopics,
  submitWriting,
  type WritingHistoryItem,
  type WritingResult,
  type WritingTopic,
} from '../../api/writing'
import './Writing.css'

/** 话题分类选项（id 与后端/DB 一致，label 用于展示） */
const CATEGORIES: { id: string; label: string }[] = [
  { id: '考研', label: '考研作文' },
  { id: '四六级', label: '四六级作文' },
  { id: '日常', label: '日常写作' },
]

/** 难度选项 */
const DIFFICULTIES: { id: string; label: string }[] = [
  { id: '初级', label: '初级' },
  { id: '中级', label: '中级' },
  { id: '高级', label: '高级' },
]

/** 预设题目（前端硬编码，按分类，每个分类 10 个） */
const PRESET_TOPICS: Record<string, string[]> = {
  考研: [
    'The Importance of Perseverance',
    'On the Importance of Time Management',
    'The Impact of Social Media on Society',
    'Why Should We Protect the Environment',
    'The Role of Education in Modern Life',
    'On Reading Habits',
    'The Advantages and Disadvantages of Remote Work',
    'How to Deal with Stress',
    'The Importance of Cultural Exchange',
    'My View on Artificial Intelligence',
  ],
  四六级: [
    '假设你是李华，给外国朋友写一封邮件介绍中国传统节日',
    '写一篇关于大学生是否应该兼职的议论文',
    '描述一次难忘的旅行经历',
    '关于心理健康重要性的短文',
    '写一封感谢信给帮助过你的老师',
    '论运动对健康的重要性',
    '描述你最喜欢的一本书',
    '关于网购利弊的讨论',
    '给新生的校园生活建议',
    '论志愿服务的意义',
  ],
  日常: [
    '写一封邮件邀请朋友参加聚会',
    '写一篇日记记录今天的经历',
    '写一段自我介绍',
    '给同事写一封工作邮件请假',
    '写一篇简短的产品评价',
    '写一封感谢信',
    '写一段旅行计划',
    '写一段节日祝福',
    '写一封投诉信（餐厅/服务）',
    '写一段周末计划',
  ],
}

/** 生成数量选项 */
const GEN_COUNTS = [1, 3, 5]

function defaultTopic(category: string): string {
  const pool = PRESET_TOPICS[category] || PRESET_TOPICS['考研']
  return pool[0]
}

/** 相对时间：刚刚 / X 分钟前 / X 小时前 / X 天前 / 具体日期 */
function formatRelativeTime(iso: string): string {
  const t = new Date(iso).getTime()
  if (Number.isNaN(t)) return ''
  const diff = Date.now() - t
  const min = Math.floor(diff / 60000)
  if (min < 1) return '刚刚'
  if (min < 60) return `${min}分钟前`
  const hour = Math.floor(min / 60)
  if (hour < 24) return `${hour}小时前`
  const day = Math.floor(hour / 24)
  if (day < 30) return `${day}天前`
  const d = new Date(iso)
  return `${d.getMonth() + 1}月${d.getDate()}日`
}

/** 根据总分返回颜色：90+ 绿色，70-89 橙色，<70 红色（知岸红） */
function scoreColor(total: number): string {
  if (total >= 90) return '#16a34a'
  if (total >= 70) return '#f59e0b'
  return '#e60012'
}

/** 单项评分进度条：标签 + 分数 + 知岸红进度条 */
function ScoreBar({ label, value, max }: { label: string; value: number; max: number }) {
  const pct = Math.max(0, Math.min(100, Math.round((value / max) * 100)))
  return (
    <div className="writing-score-bar-item">
      <div className="writing-score-bar-head">
        <span className="writing-score-bar-label">{label}</span>
        <span className="writing-score-bar-value">{value}</span>
      </div>
      <div className="writing-score-bar-track">
        <div className="writing-score-bar-fill" style={{ width: `${pct}%` }} />
      </div>
    </div>
  )
}

/** 英语写作练习：写作区 + AI 批改反馈 + 辅助功能 三栏布局 */
export default function WritingPractice() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'

  const [category, setCategory] = useState('考研')
  const [difficulty, setDifficulty] = useState('初级')
  const [topic, setTopic] = useState(defaultTopic('考研'))
  const [content, setContent] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState<WritingResult | null>(null)
  const [status, setStatus] = useState<'idle' | 'loading' | 'done' | 'error'>('idle')
  const [error, setError] = useState('')
  const [history, setHistory] = useState<WritingHistoryItem[]>([])
  const [sampleOpen, setSampleOpen] = useState(false)

  // 题目相关
  const [generatedTopics, setGeneratedTopics] = useState<WritingTopic[]>([])
  const [genModalOpen, setGenModalOpen] = useState(false)
  const [genCategory, setGenCategory] = useState('考研')
  const [genCount, setGenCount] = useState(3)
  const [generating, setGenerating] = useState(false)
  const [genError, setGenError] = useState('')

  const wordCount = content.trim() ? content.trim().split(/\s+/).length : 0

  const loadHistory = async () => {
    try {
      const res = await getWritingHistory()
      setHistory(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const loadGeneratedTopics = async (cat: string) => {
    try {
      const res = await getWritingTopics(cat)
      setGeneratedTopics(res.data)
    } catch {
      setGeneratedTopics([])
    }
  }

  useEffect(() => {
    loadHistory()
    loadGeneratedTopics('考研')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const handleCategoryChange = (id: string) => {
    setCategory(id)
    setTopic(defaultTopic(id))
    loadGeneratedTopics(id)
  }

  const handleSubmit = async () => {
    const text = content.trim()
    if (!text) {
      setError('请先写下你的作文')
      return
    }
    if (!topic.trim()) {
      setError('请填写作文题目')
      return
    }
    setSubmitting(true)
    setStatus('loading')
    setError('')
    try {
      const res = await submitWriting({
        topic: topic.trim(),
        category,
        difficulty,
        content: text,
      })
      setResult(res.data)
      setStatus('done')
      setSampleOpen(false)
      await loadHistory()
    } catch (err) {
      setStatus('error')
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  const handleViewHistory = async (id: number) => {
    try {
      const res = await getWritingDetail(id)
      const detail = res.data
      setResult(detail)
      setStatus('done')
      setCategory(detail.category || '考研')
      setDifficulty(detail.difficulty || '初级')
      setTopic(detail.topic)
      setContent(detail.content)
      setSampleOpen(false)
      setError('')
      loadGeneratedTopics(detail.category || '考研')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  // ---------- AI 生成题目 ----------

  const openGenModal = () => {
    setGenCategory(category)
    setGenCount(3)
    setGenError('')
    setGenModalOpen(true)
  }

  const closeGenModal = () => {
    if (generating) return
    setGenModalOpen(false)
  }

  const handleGenerate = async () => {
    setGenerating(true)
    setGenError('')
    try {
      await generateTopics(genCategory, genCount)
      setGenModalOpen(false)
      // 若生成的分类与当前不一致，切过去，保证新题目立刻可见
      if (genCategory !== category) {
        setCategory(genCategory)
        setTopic(defaultTopic(genCategory))
      }
      await loadGeneratedTopics(genCategory)
    } catch (err) {
      setGenError(getErrorMessage(err))
    } finally {
      setGenerating(false)
    }
  }

  // 合并预设 + 管理员生成题目（去重，预设在前）
  const allTopics = Array.from(
    new Set([...(PRESET_TOPICS[category] || []), ...generatedTopics.map((t) => t.topic)]),
  )

  return (
    <div className="writing-layout">
      <div className="writing-cards">
        {/* 左栏：写作区 */}
        <section className="writing-col writing-write">
          <header className="writing-col-header">写作练习</header>
          <div className="writing-write-body">
            <div className="writing-topic">
              <span className="writing-topic-label">题目</span>
              <input
                className="writing-topic-input"
                value={topic}
                onChange={(e) => setTopic(e.target.value)}
                placeholder="输入或修改作文题目"
              />
            </div>
            <textarea
              className="writing-textarea"
              value={content}
              onChange={(e) => setContent(e.target.value)}
              placeholder="在这里写下你的英语作文..."
            />
            <div className="writing-write-footer">
              <span className="writing-word-count">{wordCount} 词</span>
              {error && <p className="writing-error">{error}</p>}
              <button
                className="writing-submit-btn"
                onClick={handleSubmit}
                disabled={submitting}
              >
                {submitting ? '批改中...' : '提交批改'}
              </button>
            </div>
          </div>
        </section>

        {/* 中栏：AI 批改反馈 */}
        <section className="writing-col writing-feedback">
          <header className="writing-col-header">AI 批改</header>
          <div className="writing-feedback-body">
            {status === 'idle' && (
              <p className="writing-feedback-placeholder">写完提交后 AI 批改</p>
            )}
            {status === 'loading' && (
              <p className="writing-feedback-placeholder">AI 批改中，请稍候...</p>
            )}
            {status === 'error' && (
              <p className="writing-feedback-placeholder">批改失败，请重试</p>
            )}
            {status === 'done' && result && (
              <div className="writing-result">
                <div className="writing-score-total">
                  <span
                    className="writing-score-total-number"
                    style={{ color: scoreColor(result.score ?? 0) }}
                  >
                    {result.score ?? '—'}
                  </span>
                  <span className="writing-score-total-unit">分</span>
                </div>

                <div className="writing-score-items">
                  <ScoreBar label="语法" value={result.feedback.grammar_score} max={40} />
                  <ScoreBar label="结构" value={result.feedback.structure_score} max={30} />
                  <ScoreBar label="用词" value={result.feedback.vocab_score} max={30} />
                </div>

                {result.feedback.errors.length > 0 && (
                  <div className="writing-errors">
                    <p className="writing-errors-title">逐句批改</p>
                    {result.feedback.errors.map((e, i) => (
                      <div key={i} className="writing-error-item">
                        {e.sentence && (
                          <div className="writing-error-line">
                            <span className="writing-error-original">{e.sentence}</span>
                            {e.sentence && e.fix && (
                              <span className="writing-error-arrow">→</span>
                            )}
                            {e.fix && <span className="writing-error-fix">{e.fix}</span>}
                          </div>
                        )}
                        {e.error && <p className="writing-error-issue">{e.error}</p>}
                      </div>
                    ))}
                  </div>
                )}

                {result.feedback.suggestions && (
                  <div className="writing-suggestions">
                    <p className="writing-suggestions-title">整体建议</p>
                    <p className="writing-suggestions-text">{result.feedback.suggestions}</p>
                  </div>
                )}

                {result.feedback.sample && (
                  <div className="writing-sample">
                    <button
                      className="writing-sample-toggle"
                      onClick={() => setSampleOpen((v) => !v)}
                    >
                      参考范文 {sampleOpen ? '▾' : '▸'}
                    </button>
                    {sampleOpen && (
                      <pre className="writing-sample-text">{result.feedback.sample}</pre>
                    )}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>

        {/* 右栏：辅助功能 */}
        <section className="writing-col writing-tools">
          <header className="writing-col-header">辅助功能</header>
          <div className="writing-tools-content">
            {isAdmin && (
              <div className="writing-tool-block">
                <button className="writing-gen-btn" onClick={openGenModal}>
                  ✨ AI 生成题目
                </button>
              </div>
            )}

            <div className="writing-tool-block">
              <p className="writing-tool-label">话题分类</p>
              <div className="writing-tool-buttons">
                {CATEGORIES.map((c) => (
                  <button
                    key={c.id}
                    className={
                      c.id === category
                        ? 'writing-tool-btn writing-tool-btn-active'
                        : 'writing-tool-btn'
                    }
                    onClick={() => handleCategoryChange(c.id)}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="writing-tool-block">
              <p className="writing-tool-label">难度选择</p>
              <div className="writing-tool-buttons">
                {DIFFICULTIES.map((d) => (
                  <button
                    key={d.id}
                    className={
                      d.id === difficulty
                        ? 'writing-tool-btn writing-tool-btn-active'
                        : 'writing-tool-btn'
                    }
                    onClick={() => setDifficulty(d.id)}
                  >
                    {d.label}
                  </button>
                ))}
              </div>
            </div>

            <div className="writing-tool-block">
              <p className="writing-tool-label">题目选择</p>
              <div className="writing-topic-list">
                {allTopics.map((t) => (
                  <button
                    key={t}
                    className={
                      t === topic
                        ? 'writing-topic-card writing-topic-card-active'
                        : 'writing-topic-card'
                    }
                    onClick={() => setTopic(t)}
                  >
                    {t}
                  </button>
                ))}
              </div>
            </div>

            <div className="writing-tool-block">
              <p className="writing-tool-label">写作历史</p>
              {history.length === 0 ? (
                <p className="writing-history-empty">还没有写作记录</p>
              ) : (
                history.slice(0, 5).map((h) => (
                  <button
                    key={h.id}
                    className="writing-history-item"
                    onClick={() => handleViewHistory(h.id)}
                  >
                    <span className="writing-history-topic">{h.topic}</span>
                    <span className="writing-history-meta">
                      {h.score != null ? `${h.score}分 · ` : ''}
                      {formatRelativeTime(h.created_at)}
                    </span>
                  </button>
                ))
              )}
            </div>
          </div>
        </section>
      </div>

      {/* AI 生成题目弹窗 */}
      {genModalOpen && (
        <div className="writing-gen-modal-overlay" onClick={closeGenModal}>
          <div className="writing-gen-modal" onClick={(e) => e.stopPropagation()}>
            <div className="writing-gen-modal-head">
              <span className="writing-gen-modal-title">✨ AI 生成题目</span>
              <button
                className="writing-gen-modal-close"
                onClick={closeGenModal}
                aria-label="关闭"
              >
                ×
              </button>
            </div>
            <div className="writing-gen-modal-body">
              <p className="writing-gen-field-label">选择分类</p>
              <div className="writing-tool-buttons">
                {CATEGORIES.map((c) => (
                  <button
                    key={c.id}
                    className={
                      genCategory === c.id
                        ? 'writing-tool-btn writing-tool-btn-active'
                        : 'writing-tool-btn'
                    }
                    onClick={() => setGenCategory(c.id)}
                  >
                    {c.label}
                  </button>
                ))}
              </div>
              <p className="writing-gen-field-label">生成数量</p>
              <div className="writing-tool-buttons">
                {GEN_COUNTS.map((n) => (
                  <button
                    key={n}
                    className={
                      genCount === n
                        ? 'writing-tool-btn writing-tool-btn-active'
                        : 'writing-tool-btn'
                    }
                    onClick={() => setGenCount(n)}
                  >
                    {n}
                  </button>
                ))}
              </div>
              {genError && <p className="writing-gen-error">{genError}</p>}
            </div>
            <div className="writing-gen-modal-foot">
              <button className="writing-gen-cancel" onClick={closeGenModal}>
                取消
              </button>
              <button
                className="writing-gen-start"
                onClick={handleGenerate}
                disabled={generating}
              >
                {generating ? '生成中...' : '开始生成'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}
