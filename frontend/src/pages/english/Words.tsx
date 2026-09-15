import { useEffect, useRef, useState } from 'react'
import type { ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import { getErrorMessage } from '../../api/client'
import { getTtsUrl } from '../../api/english'
import {
  getBooks,
  getSettings,
  getStats,
  getTodayQueue,
  getWordDetail,
  selectBook,
  submitReview,
  updateSettings,
  type BookItem,
  type BookKey,
  type Feedback,
  type TodayQueueItem,
  type WordDetail,
  type WordSettings,
  type WordStats,
} from '../../api/words'
import './Words.css'

type WordsView = 'review' | 'select' | 'stats'

/** 词性英文缩写 → 中文单字标签（如 n. → 名、adj. → 形），未知则原样返回 */
const POS_CN: Record<string, string> = {
  'n.': '名',
  'v.': '动',
  'vi.': '动',
  'vt.': '动',
  'adj.': '形',
  'adv.': '副',
  'prep.': '介',
  'conj.': '连',
  'pron.': '代',
  'num.': '数',
  'art.': '冠',
  'int.': '叹',
  'aux.': '助',
  'det.': '限',
}

function posLabel(pos: string | null): string {
  if (!pos) return ''
  const p = pos.trim()
  return POS_CN[p.toLowerCase()] ?? p
}

/** 例句中目标单词高亮（不区分大小写，返回可渲染节点） */
function highlightTarget(text: string, target: string): ReactNode {
  if (!text || !target) return text
  const escaped = target.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
  const parts = text.split(new RegExp(`(${escaped})`, 'ig'))
  return parts.map((part, i) =>
    part.toLowerCase() === target.toLowerCase() ? (
      <span key={i} className="review-hl">
        {part}
      </span>
    ) : (
      part
    ),
  )
}

// ============================================================ 页面外壳

export default function Words() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [view, setView] = useState<WordsView>('review')

  const navItems: { key: WordsView; label: string }[] = [
    { key: 'review', label: '复习' },
    { key: 'select', label: '选词' },
    { key: 'stats', label: '统计' },
  ]

  return (
    <div className="words-page">
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

      <div className="words-body">
        <aside className="words-sidenav">
          <div className="words-sidenav-title">背单词</div>
          <nav className="words-sidenav-menu">
            {navItems.map((item) => (
              <button
                key={item.key}
                className={`words-sidenav-item ${view === item.key ? 'is-active' : ''}`}
                onClick={() => setView(item.key)}
              >
                {item.label}
              </button>
            ))}
          </nav>
          <button className="words-sidenav-back" onClick={() => navigate('/english')}>
            ← 返回英语主页
          </button>
        </aside>

        <main className="words-content">
          <div className="words-container">
            {view === 'review' && <ReviewPanel onNavigate={setView} />}
            {view === 'select' && <SelectPanel />}
            {view === 'stats' && <StatsPanel />}
          </div>
        </main>
      </div>
    </div>
  )
}

// ============================================================ 复习页

function ReviewPanel({ onNavigate }: { onNavigate: (v: WordsView) => void }) {
  const [queue, setQueue] = useState<TodayQueueItem[]>([])
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState<WordDetail | null>(null)
  const [flipped, setFlipped] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const [knownCount, setKnownCount] = useState(0)
  const [vagueCount, setVagueCount] = useState(0)
  const [forgottenCount, setForgottenCount] = useState(0)

  const initializedRef = useRef(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const advanceTimerRef = useRef<number | null>(null)

  const currentItem = queue[index] ?? null
  const finished = queue.length > 0 && index >= queue.length

  // 初次加载队列
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    ;(async () => {
      try {
        const res = await getTodayQueue()
        setQueue(res.data.items)
      } catch (err) {
        setError(getErrorMessage(err))
      }
      setLoading(false)
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 切换单词时拉详情
  useEffect(() => {
    if (!currentItem) return
    setFlipped(false)
    setResult('')
    setDetail(null)
    ;(async () => {
      try {
        const res = await getWordDetail(currentItem.id)
        setDetail(res.data)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [currentItem])

  const playWord = () => {
    if (!currentItem) return
    if (audioRef.current) audioRef.current.pause()
    const audio = new Audio(getTtsUrl(currentItem.word, 1))
    audioRef.current = audio
    audio.play().catch(() => {})
  }

  const doReview = async (feedback: Feedback) => {
    if (!currentItem || submitting) return
    setSubmitting(true)
    try {
      const res = await submitReview(currentItem.id, feedback)
      const data = res.data

      if (feedback === 'known') setKnownCount((k) => k + 1)
      else if (feedback === 'vague') setVagueCount((v) => v + 1)
      else setForgottenCount((f) => f + 1)

      const prev = Math.round(currentItem.current_strength)
      const next = Math.round(data.new_strength)
      setResult(`S ${prev}→${next}`)

      advanceTimerRef.current = window.setTimeout(() => {
        setResult('')
        setFlipped(false)
        setSubmitting(false)
        setIndex((i) => i + 1)
      }, 1000)
    } catch (err) {
      setError(getErrorMessage(err))
      setSubmitting(false)
    }
  }

  const doReviewRef = useRef(doReview)
  doReviewRef.current = doReview

  // 键盘：空格翻面，1=不认识 2=不确定 3=认识
  useEffect(() => {
    function onKey(e: KeyboardEvent) {
      if (loading || finished || submitting) return
      if (e.code === 'Space' || e.key === ' ') {
        e.preventDefault()
        if (!flipped) setFlipped(true)
        return
      }
      if (!flipped) return
      if (e.key === '1') doReviewRef.current('forgotten')
      else if (e.key === '2') doReviewRef.current('vague')
      else if (e.key === '3') doReviewRef.current('known')
    }
    window.addEventListener('keydown', onKey)
    return () => window.removeEventListener('keydown', onKey)
  }, [loading, finished, submitting, flipped])

  // 卸载清理
  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause()
      if (advanceTimerRef.current) window.clearTimeout(advanceTimerRef.current)
    }
  }, [])

  const restart = () => {
    setKnownCount(0)
    setVagueCount(0)
    setForgottenCount(0)
    setIndex(0)
    setFlipped(false)
    setResult('')
    setDetail(null)
    setLoading(true)
    getTodayQueue()
      .then((res) => setQueue(res.data.items))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }

  const total = queue.length
  const remaining = total - index
  const progressPercent = total > 0 ? (index / total) * 100 : 0
  const totalLearnedSession = knownCount + vagueCount + forgottenCount

  return (
    <div className="review-panel">
      {loading ? (
        <div className="review-loading">加载中...</div>
      ) : error && total === 0 ? (
        <div className="review-empty">
          <div className="review-empty-icon">⚠️</div>
          <p className="review-empty-text">{error}</p>
        </div>
      ) : total === 0 ? (
        <div className="review-empty">
          <div className="review-empty-icon">✅</div>
          <p className="review-empty-text">今日任务已完成</p>
          <button className="review-done-btn" onClick={() => onNavigate('select')}>
            去选词
          </button>
        </div>
      ) : finished ? (
        <div className="review-done">
          <div className="review-done-icon">🎉</div>
          <h2 className="review-done-title">本次学习完成</h2>
          <p className="review-done-summary">共学习 {totalLearnedSession} 个单词</p>
          <div className="review-done-counts">
            <span className="review-done-known">认识 {knownCount}</span>
            <span className="review-done-vague">不确定 {vagueCount}</span>
            <span className="review-done-forgotten">不认识 {forgottenCount}</span>
          </div>
          <div className="review-done-actions">
            <button className="review-done-btn ghost" onClick={() => onNavigate('select')}>
              返回选词
            </button>
            <button className="review-done-btn" onClick={restart}>
              再学一组
            </button>
          </div>
        </div>
      ) : (
        currentItem && (
          <>
            <div className="review-card">
              {/* 顶部进度 */}
              <div className="review-top">
                <span className="review-remaining">
                  今日剩余 {remaining} 个（第 {index + 1} / 共 {total}）
                </span>
                <div className="review-progress-track">
                  <div
                    className="review-progress-fill"
                    style={{ width: `${progressPercent}%` }}
                  />
                </div>
              </div>

              {/* 单词头：翻面保持不变 */}
              <div className="review-word-row">
                <h2 className="review-word">{currentItem.word}</h2>
                <div className="review-meta">
                  <span className="review-accent">美</span>
                  <span className="review-phonetic">{currentItem.phonetic ?? ''}</span>
                  <button
                    className="review-speak"
                    onClick={playWord}
                    title="发音"
                    aria-label="发音"
                  >
                    <svg
                      viewBox="0 0 24 24"
                      width="20"
                      height="20"
                      fill="currentColor"
                      aria-hidden="true"
                    >
                      <path d="M3 9v6h4l5 5V4L7 9H3zm13.5 3c0-1.77-1.02-3.29-2.5-4.03v8.05c1.48-.73 2.5-2.25 2.5-4.02zM14 3.23v2.06c2.89.86 5 3.54 5 6.71s-2.11 5.85-5 6.71v2.06c4.01-.91 7-4.49 7-8.77s-2.99-7.86-7-8.77z" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* 主体：正面回忆 / 背面答案 */}
              <div
                className="review-body"
                onClick={() => {
                  if (!flipped && !submitting) setFlipped(true)
                }}
              >
                {!flipped ? (
                  <div className="review-recall">
                    <p className="review-recall-hint">请回忆单词发音和释义</p>
                    <p className="review-recall-sub">点击卡片或按空格键显示答案</p>
                  </div>
                ) : (
                  <div className="review-answer">
                    <div className="review-definitions">
                      {detail ? (
                        detail.definitions.map((d, i) => (
                          <div className="review-definition" key={i}>
                            {d.pos && <span className="review-pos">[{posLabel(d.pos)}]</span>}
                            <span className="review-meaning">{d.meaning}</span>
                          </div>
                        ))
                      ) : (
                        <p className="review-loading-inline">加载中...</p>
                      )}
                    </div>

                    {detail && detail.examples.length > 0 && (
                      <div className="review-examples">
                        <div className="review-examples-title">例句</div>
                        {detail.examples.map((e, i) => (
                          <div className="review-example" key={i}>
                            <p className="review-example-en">
                              {highlightTarget(e.en, currentItem.word)}
                            </p>
                            {e.zh && <p className="review-example-zh">{e.zh}</p>}
                          </div>
                        ))}
                      </div>
                    )}

                    {result ? (
                      <div className="review-result">{result}</div>
                    ) : (
                      <div className="review-feedback">
                        <button
                          className="review-fb review-fb-forgotten"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('forgotten')
                          }}
                          disabled={submitting}
                        >
                          <span className="review-fb-label">
                            不认识 <kbd>1</kbd>
                          </span>
                          <span className="review-fb-preview">
                            {currentItem.previews.forgotten.text}
                          </span>
                        </button>
                        <button
                          className="review-fb review-fb-vague"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('vague')
                          }}
                          disabled={submitting}
                        >
                          <span className="review-fb-label">
                            不确定 <kbd>2</kbd>
                          </span>
                          <span className="review-fb-preview">
                            {currentItem.previews.vague.text}
                          </span>
                        </button>
                        <button
                          className="review-fb review-fb-known"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('known')
                          }}
                          disabled={submitting}
                        >
                          <span className="review-fb-label">
                            认识 <kbd>3</kbd>
                          </span>
                          <span className="review-fb-preview">
                            {currentItem.previews.known.text}
                          </span>
                        </button>
                      </div>
                    )}
                  </div>
                )}
              </div>
            </div>
            {error && <p className="review-error">{error}</p>}
          </>
        )
      )}
    </div>
  )
}

// ============================================================ 选词页

function SelectPanel() {
  const [books, setBooks] = useState<BookItem[]>([])
  const [settings, setSettings] = useState<WordSettings | null>(null)
  const [queueCounts, setQueueCounts] = useState<{ review: number; newCount: number }>({
    review: 0,
    newCount: 0,
  })
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')
  const [search, setSearch] = useState('')
  const [editingGoal, setEditingGoal] = useState(false)
  const [goalInput, setGoalInput] = useState('')

  const load = async () => {
    try {
      const [booksRes, settingsRes, queueRes] = await Promise.all([
        getBooks(),
        getSettings(),
        getTodayQueue(),
      ])
      setBooks(booksRes.data)
      setSettings(settingsRes.data)
      setQueueCounts({
        review: queueRes.data.review_count,
        newCount: queueRes.data.new_count,
      })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    load()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  const startEditGoal = () => {
    setGoalInput(String(settings?.daily_new_goal ?? 20))
    setEditingGoal(true)
  }

  const commitGoal = async () => {
    const val = parseInt(goalInput, 10)
    setEditingGoal(false)
    if (!Number.isFinite(val) || val < 1 || val > 200) return
    try {
      const res = await updateSettings(val)
      setSettings(res.data)
      const queueRes = await getTodayQueue()
      setQueueCounts({
        review: queueRes.data.review_count,
        newCount: queueRes.data.new_count,
      })
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const switchBook = async (key: BookKey) => {
    if (key === settings?.current_book) return
    try {
      const res = await selectBook(key)
      setSettings(res.data)
      const queueRes = await getTodayQueue()
      setQueueCounts({
        review: queueRes.data.review_count,
        newCount: queueRes.data.new_count,
      })
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const q = search.trim().toLowerCase()
  const filteredBooks = q
    ? books.filter((b) => b.label.toLowerCase().includes(q) || b.key.includes(q))
    : books

  return (
    <div className="select-panel">
      {loading ? (
        <div className="review-loading">加载中...</div>
      ) : (
        <>
          {/* 顶部统计区 */}
          <div className="select-stats">
            <div className="select-stat">
              {editingGoal ? (
                <input
                  className="select-goal-input"
                  type="number"
                  min={1}
                  max={200}
                  value={goalInput}
                  autoFocus
                  onChange={(e) => setGoalInput(e.target.value)}
                  onBlur={commitGoal}
                  onKeyDown={(e) => {
                    if (e.key === 'Enter') (e.target as HTMLInputElement).blur()
                  }}
                />
              ) : (
                <button
                  className="select-goal-value"
                  onClick={startEditGoal}
                  title="点击调整"
                >
                  {settings?.daily_new_goal ?? 20}
                </button>
              )}
              <span className="select-stat-label">每日学习量</span>
            </div>
            <div className="select-stat">
              <span className="select-stat-value">{queueCounts.review}</span>
              <span className="select-stat-label">待复习</span>
            </div>
            <div className="select-stat">
              <span className="select-stat-value">{queueCounts.newCount}</span>
              <span className="select-stat-label">待新学</span>
            </div>
            <div className="select-stat">
              <span className="select-stat-value">英→中</span>
              <span className="select-stat-label">记忆模式</span>
            </div>
          </div>

          {/* 搜索框 */}
          <div className="select-search">
            <input
              placeholder="搜索词书"
              value={search}
              onChange={(e) => setSearch(e.target.value)}
            />
          </div>

          {/* 词书列表 */}
          <div className="select-books">
            {filteredBooks.map((book) => {
              const isCurrent = book.key === settings?.current_book
              const pct = book.total > 0 ? Math.round((book.learned / book.total) * 100) : 0
              return (
                <div
                  key={book.key}
                  className={`select-book ${isCurrent ? 'is-current' : ''}`}
                  onClick={() => switchBook(book.key)}
                >
                  <div className="select-book-head">
                    <span className="select-book-name">{book.label}</span>
                    <span className="select-book-state">
                      {isCurrent ? '当前学习 ✓' : '点击切换'}
                    </span>
                  </div>
                  <div className="select-book-progress">
                    <div className="select-book-progress-track">
                      <div
                        className="select-book-progress-fill"
                        style={{ width: `${pct}%` }}
                      />
                    </div>
                  </div>
                  <div className="select-book-stats">
                    <span className="s-familiar">熟悉 {book.familiar}</span>
                    <span className="s-medium">一般 {book.medium}</span>
                    <span className="s-weak">不熟 {book.weak}</span>
                    <span className="s-unlearned">未学 {book.unlearned}</span>
                  </div>
                  <div className="select-book-count">
                    已学 {book.learned} / 共 {book.total}
                  </div>
                </div>
              )
            })}
          </div>

          {error && <p className="review-error">{error}</p>}
        </>
      )}
    </div>
  )
}

// ============================================================ 统计页

function StatsPanel() {
  const [stats, setStats] = useState<WordStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    getStats()
      .then((r) => setStats(r.data))
      .catch((err) => setError(getErrorMessage(err)))
      .finally(() => setLoading(false))
  }, [])

  if (loading) return <div className="review-loading">加载中...</div>
  if (error && !stats) return <div className="review-empty">⚠️ {error}</div>

  const known = stats?.known_count ?? 0
  const vague = stats?.vague_count ?? 0
  const forgotten = stats?.forgotten_count ?? 0
  const fbTotal = known + vague + forgotten
  const accuracy = Math.round((stats?.accuracy ?? 0) * 100)

  return (
    <div className="stats-panel">
      <div className="stats-grid">
        <div className="stats-card">
          <span className="stats-value">{stats?.learned ?? 0}</span>
          <span className="stats-label">已学总数</span>
        </div>
        <div className="stats-card">
          <span className="stats-value">{stats?.due_today ?? 0}</span>
          <span className="stats-label">今日待复习</span>
        </div>
        <div className="stats-card">
          <span className="stats-value">{stats?.learned_today ?? 0}</span>
          <span className="stats-label">今日已学</span>
        </div>
        <div className="stats-card">
          <span className="stats-value">{stats?.mastered ?? 0}</span>
          <span className="stats-label">已掌握</span>
        </div>
        <div className="stats-card">
          <span className="stats-value">{stats?.streak_days ?? 0}</span>
          <span className="stats-label">连续学习(天)</span>
        </div>
      </div>

      <div className="stats-block">
        <div className="stats-block-title">反馈累计</div>
        <div className="stats-bar-row">
          <span className="stats-bar-label">认识</span>
          <div className="stats-bar-track">
            <div
              className="stats-bar-fill known"
              style={{ width: `${fbTotal ? (known / fbTotal) * 100 : 0}%` }}
            />
          </div>
          <span className="stats-bar-value">{known}</span>
        </div>
        <div className="stats-bar-row">
          <span className="stats-bar-label">不确定</span>
          <div className="stats-bar-track">
            <div
              className="stats-bar-fill vague"
              style={{ width: `${fbTotal ? (vague / fbTotal) * 100 : 0}%` }}
            />
          </div>
          <span className="stats-bar-value">{vague}</span>
        </div>
        <div className="stats-bar-row">
          <span className="stats-bar-label">不认识</span>
          <div className="stats-bar-track">
            <div
              className="stats-bar-fill forgotten"
              style={{ width: `${fbTotal ? (forgotten / fbTotal) * 100 : 0}%` }}
            />
          </div>
          <span className="stats-bar-value">{forgotten}</span>
        </div>
      </div>

      <div className="stats-block">
        <div className="stats-block-title">正确率</div>
        <div className="stats-bar-row">
          <span className="stats-bar-label">认识占比</span>
          <div className="stats-bar-track">
            <div className="stats-bar-fill known" style={{ width: `${accuracy}%` }} />
          </div>
          <span className="stats-bar-value">{accuracy}%</span>
        </div>
      </div>
    </div>
  )
}
