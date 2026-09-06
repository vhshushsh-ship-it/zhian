import { useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import { getErrorMessage } from '../../api/client'
import { getTtsUrl } from '../../api/english'
import {
  getStats,
  getTodayQueue,
  getWordDetail,
  submitReview,
  type Feedback,
  type TodayQueueItem,
  type WordDetail,
  type WordStats,
} from '../../api/words'
import './Words.css'

/** 记忆强度颜色：<30 红、30-70 黄、>70 绿 */
function strengthColor(s: number): string {
  if (s < 30) return '#e60012'
  if (s <= 70) return '#ffc107'
  return '#22c55e'
}

export default function Words() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const [queue, setQueue] = useState<TodayQueueItem[]>([])
  const [index, setIndex] = useState(0)
  const [detail, setDetail] = useState<WordDetail | null>(null)
  const [flipped, setFlipped] = useState(false)
  const [stats, setStats] = useState<WordStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [submitting, setSubmitting] = useState(false)
  const [result, setResult] = useState('')
  const [error, setError] = useState('')

  // 本次 session 三档计数（用于完成页总结）
  const [knownCount, setKnownCount] = useState(0)
  const [vagueCount, setVagueCount] = useState(0)
  const [forgottenCount, setForgottenCount] = useState(0)

  const initializedRef = useRef(false)
  const audioRef = useRef<HTMLAudioElement | null>(null)
  const advanceTimerRef = useRef<number | null>(null)

  const currentItem = queue[index] ?? null
  const finished = queue.length > 0 && index >= queue.length

  // 初次加载：队列 + 统计（分别处理，统计失败不阻塞学习）
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    ;(async () => {
      try {
        const queueRes = await getTodayQueue()
        setQueue(queueRes.data.items)
      } catch (err) {
        setError(getErrorMessage(err))
      }
      try {
        const statsRes = await getStats()
        setStats(statsRes.data)
      } catch {
        // 统计拉取失败不阻塞学习
      }
      setLoading(false)
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 切换单词时拉取详情
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

  // 完成后重新拉统计
  useEffect(() => {
    if (finished) {
      getStats().then((r) => setStats(r.data)).catch(() => {})
    }
  }, [finished])

  const refreshStats = () => {
    getStats().then((r) => setStats(r.data)).catch(() => {})
  }

  /** 播放单词发音（美式 TTS） */
  const playWord = () => {
    if (!currentItem) return
    if (audioRef.current) audioRef.current.pause()
    const audio = new Audio(getTtsUrl(currentItem.word, 1))
    audioRef.current = audio
    audio.play().catch(() => {})
  }

  /** 提交复习反馈 */
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
      setResult(`S ${prev}→${next}，${data.interval_text}后复习`)

      refreshStats()

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

  // 键盘快捷键：空格翻面，1=忘记 2=模糊 3=认识
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

  // 卸载清理：暂停音频、清理定时器
  useEffect(() => {
    return () => {
      if (audioRef.current) audioRef.current.pause()
      if (advanceTimerRef.current) window.clearTimeout(advanceTimerRef.current)
    }
  }, [])

  // 整体进度条：已学 /（已学 + 待学）
  const learned = stats?.learned ?? 0
  const dueToday = queue.length
  const progressDenom = learned + dueToday
  const progressPercent = progressDenom > 0 ? Math.round((learned / progressDenom) * 100) : 0
  const totalLearnedSession = knownCount + vagueCount + forgottenCount

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

      <main className="words-main">
        {/* 顶部统计栏 */}
        <section className="words-stats">
          <div className="words-stat-card">
            <span className="words-stat-value">{dueToday}</span>
            <span className="words-stat-label">今日待学</span>
          </div>
          <div className="words-stat-card">
            <span className="words-stat-value">{learned}</span>
            <span className="words-stat-label">已学</span>
          </div>
          <div className="words-stat-card">
            <span className="words-stat-value">{stats?.mastered ?? 0}</span>
            <span className="words-stat-label">已掌握</span>
          </div>
          <div className="words-stat-card">
            <span className="words-stat-value">{stats?.streak_days ?? 0}</span>
            <span className="words-stat-label">连续学习(天)</span>
          </div>
        </section>

        {/* 整体进度条 */}
        <div className="words-progress">
          <div className="words-progress-track">
            <div className="words-progress-fill" style={{ width: `${progressPercent}%` }} />
          </div>
          <span className="words-progress-text">
            已学 {learned} · 待学 {dueToday}
          </span>
        </div>

        {/* 主体内容 */}
        {loading ? (
          <div className="words-loading">加载中...</div>
        ) : error && queue.length === 0 ? (
          <div className="words-empty">
            <div className="words-empty-icon">⚠️</div>
            <p className="words-empty-text">{error}</p>
          </div>
        ) : finished ? (
          <div className="words-done">
            <div className="words-done-icon">🎉</div>
            <h2 className="words-done-title">本次学习完成</h2>
            <p className="words-done-summary">共学习 {totalLearnedSession} 个单词</p>
            <div className="words-done-counts">
              <span className="words-done-known">认识 {knownCount}</span>
              <span className="words-done-vague">模糊 {vagueCount}</span>
              <span className="words-done-forgotten">忘记 {forgottenCount}</span>
            </div>
            <button className="words-done-btn" onClick={() => navigate('/english')}>
              返回英语主页
            </button>
          </div>
        ) : queue.length === 0 ? (
          <div className="words-empty">
            <div className="words-empty-icon">✅</div>
            <p className="words-empty-text">今日任务已完成，明天再来</p>
          </div>
        ) : (
          currentItem && (
            <>
              <div
                className="words-card"
                onClick={() => {
                  if (!flipped && !submitting) setFlipped(true)
                }}
              >
                <div className={`words-card-inner ${flipped ? 'is-flipped' : ''}`}>
                  {/* 正面：单词 + 发音 + 记忆强度 */}
                  <div className="words-card-face words-card-front">
                    <span className={`words-tag ${currentItem.is_new ? '' : 'words-tag-review'}`}>
                      {currentItem.is_new ? '新词' : '复习'}
                    </span>
                    <h2 className="words-word">{currentItem.word}</h2>
                    <p className="words-phonetic">{currentItem.phonetic ?? ''}</p>
                    <button
                      className="words-speak-btn"
                      onClick={(e) => {
                        e.stopPropagation()
                        playWord()
                      }}
                      title="发音"
                      aria-label="发音"
                    >
                      🔊
                    </button>
                    <div className="words-strength">
                      <div className="words-strength-bar">
                        <div
                          className="words-strength-fill"
                          style={{
                            width: `${Math.min(100, Math.max(0, currentItem.current_strength))}%`,
                            background: strengthColor(currentItem.current_strength),
                          }}
                        />
                      </div>
                      <span className="words-strength-label">
                        记忆强度 {Math.round(currentItem.current_strength)}
                      </span>
                    </div>
                    <button className="words-flip-btn" type="button">
                      显示释义
                    </button>
                  </div>

                  {/* 背面：释义 + 例句 + 反馈按钮 */}
                  <div className="words-card-face words-card-back">
                    <div className="words-definitions">
                      {detail ? (
                        detail.definitions.map((d, i) => (
                          <div className="words-definition" key={i}>
                            {d.pos && <span className="words-pos">{d.pos}</span>}
                            <span className="words-meaning">{d.meaning}</span>
                          </div>
                        ))
                      ) : (
                        <p className="words-loading-inline">加载中...</p>
                      )}
                    </div>
                    {detail && detail.examples.length > 0 && (
                      <div className="words-example">
                        <p className="words-example-en">{detail.examples[0].en}</p>
                        {detail.examples[0].zh && (
                          <p className="words-example-zh">{detail.examples[0].zh}</p>
                        )}
                      </div>
                    )}
                    {result ? (
                      <div className="words-result">{result}</div>
                    ) : (
                      <div className="words-feedback">
                        <button
                          className="words-feedback-btn words-feedback-forgotten"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('forgotten')
                          }}
                          disabled={submitting}
                        >
                          忘记 <kbd>1</kbd>
                        </button>
                        <button
                          className="words-feedback-btn words-feedback-vague"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('vague')
                          }}
                          disabled={submitting}
                        >
                          模糊 <kbd>2</kbd>
                        </button>
                        <button
                          className="words-feedback-btn words-feedback-known"
                          onClick={(e) => {
                            e.stopPropagation()
                            doReview('known')
                          }}
                          disabled={submitting}
                        >
                          认识 <kbd>3</kbd>
                        </button>
                      </div>
                    )}
                  </div>
                </div>
              </div>
              {error && <p className="words-error">{error}</p>}
            </>
          )
        )}
      </main>

      <button className="words-back" onClick={() => navigate('/english')}>
        ← 返回英语主页
      </button>
    </div>
  )
}
