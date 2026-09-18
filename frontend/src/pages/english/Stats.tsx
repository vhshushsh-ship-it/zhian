import { useEffect, useRef, useState, type ReactNode } from 'react'
import { useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../../api/client'
import { createAiConversation, sendAiMessage } from '../../api/aiTutor'
import { getEnglishStats, type EnglishStats } from '../../api/stats'
import './Stats.css'

/** AI 动态建议固定提示词（context 传「英语主页」= 'english'） */
const ANALYSIS_PROMPT = '请根据我的学习数据，给出具体的学习建议和改进方向'

/** 近 7 天趋势柱状图的三个分段的配色与文案 */
const TREND_SEGMENTS = [
  { key: 'words_reviewed', label: '复习词', color: '#e60012' },
  { key: 'words_new', label: '新词', color: '#ff8f7a' },
  { key: 'speaking_messages', label: '口语消息', color: '#4f8cff' },
] as const

type TrendKey = (typeof TREND_SEGMENTS)[number]['key']

/** 把 **加粗** 渲染成 <strong>，其余原样（配合 CSS 的 pre-wrap 保留换行） */
function renderBold(text: string): ReactNode[] {
  const segments = text.split(/(\*\*[^*]+\*\*)/g)
  return segments.map((seg, i) => {
    if (seg.startsWith('**') && seg.endsWith('**') && seg.length > 4) {
      return <strong key={i}>{seg.slice(2, -2)}</strong>
    }
    return <span key={i}>{seg}</span>
  })
}

/** 'YYYY-MM-DD' → 'M/D' */
function formatDay(iso: string): string {
  const [y, m, d] = iso.split('-')
  if (!m || !d) return iso
  return `${Number(m)}/${Number(d)}`
}

/** ISO 时间 → 'YYYY-MM-DD HH:mm' */
function formatDateTime(iso: string | null): string {
  if (!iso) return '暂无'
  const t = new Date(iso)
  if (Number.isNaN(t.getTime())) return '暂无'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())} ${pad(t.getHours())}:${pad(t.getMinutes())}`
}

/** 英语模块学习数据视图（嵌入英语首页右侧内容区） */
export function StatsContent() {
  const navigate = useNavigate()

  const [stats, setStats] = useState<EnglishStats | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // AI 动态建议
  const [analysis, setAnalysis] = useState('')
  const [analysisLoading, setAnalysisLoading] = useState(false)
  const [analysisError, setAnalysisError] = useState('')
  const convIdRef = useRef<number | null>(null)
  const analysisStartedRef = useRef(false)

  /** 拉取学习数据 */
  const loadStats = async () => {
    try {
      const res = await getEnglishStats()
      setStats(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  /** 触发 AI 分析（复用同一个导师对话，避免每次新建污染历史列表） */
  const runAnalysis = async () => {
    setAnalysisLoading(true)
    setAnalysisError('')
    try {
      if (convIdRef.current == null) {
        const res = await createAiConversation()
        convIdRef.current = res.data.id
      }
      const res = await sendAiMessage(convIdRef.current, ANALYSIS_PROMPT, 'english')
      setAnalysis(res.data.ai_reply)
    } catch (err) {
      setAnalysisError(getErrorMessage(err))
    } finally {
      setAnalysisLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
    // 初次进入自动分析一次（StrictMode 下用 ref 防重复）
    if (!analysisStartedRef.current) {
      analysisStartedRef.current = true
      void runAnalysis()
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  if (loading) {
    return <div className="stats-loading">加载中...</div>
  }

  const overview = stats?.overview
  const words = stats?.words
  const speaking = stats?.speaking
  const trend = stats?.weekly_trend ?? []

  // 柱状图缩放：以 7 天中单日总量最大值为满高
  const maxTotal = Math.max(
    1,
    ...trend.map((t) => t.words_reviewed + t.words_new + t.speaking_messages),
  )
  // 常练话题：以最高次数为满宽
  const maxTopic = Math.max(1, ...(speaking?.topics ?? []).map((t) => t.count))

  return (
    <div className="stats-container">
      <header className="stats-header">
        <h2 className="stats-title">学习数据</h2>
        <span className="stats-title-accent" aria-hidden="true" />
        <p className="stats-subtitle">实时同步你的学习进度</p>
      </header>

      {error && <p className="stats-error">{error}</p>}

      {/* 概览区 */}
      <section className="stats-overview">
        <div className="stats-overview-card">
          <span className="stats-overview-icon" aria-hidden="true">🔥</span>
          <span className="stats-overview-value">{overview?.streak_days ?? 0}</span>
          <span className="stats-overview-label">连续学习（天）</span>
        </div>
        <div className="stats-overview-card">
          <span className="stats-overview-icon" aria-hidden="true">📚</span>
          <span className="stats-overview-value">{overview?.total_words_learned ?? 0}</span>
          <span className="stats-overview-label">
            已学单词（掌握 {overview?.total_words_mastered ?? 0} 词）
          </span>
        </div>
        <div className="stats-overview-card">
          <span className="stats-overview-icon" aria-hidden="true">🎤</span>
          <span className="stats-overview-value">{overview?.speaking_sessions ?? 0}</span>
          <span className="stats-overview-label">口语练习（次）</span>
        </div>
        <div className="stats-overview-card">
          <span className="stats-overview-icon" aria-hidden="true">📊</span>
          <span className="stats-overview-value">{overview?.weekly_completion_rate ?? 0}%</span>
          <span className="stats-overview-label">本周完成率</span>
        </div>
        <div className="stats-overview-card">
          <span className="stats-overview-icon" aria-hidden="true">🔍</span>
          <span className="stats-overview-value">{overview?.reading_articles_read ?? 0}</span>
          <span className="stats-overview-label">外刊精读（篇）</span>
        </div>
      </section>

      {/* 单词学习详情 */}
      <section className="stats-section">
        <h2 className="stats-section-title">单词学习</h2>
        <div className="stats-words-row">
          <div className="stats-words-cell">
            <span className="stats-words-value">{words?.current_book ?? '未设置'}</span>
            <span className="stats-words-label">当前词书</span>
          </div>
          <div className="stats-words-cell">
            <span className="stats-words-value">{words?.daily_goal ?? 20}</span>
            <span className="stats-words-label">每日目标（词）</span>
          </div>
          <div className="stats-words-cell">
            <span className="stats-words-value">{overview?.words_today_due ?? 0}</span>
            <span className="stats-words-label">今日待复习</span>
          </div>
        </div>

        <div className="stats-recognition">
          <div className="stats-recognition-head">
            <span className="stats-recognition-label">认识率</span>
            <span className="stats-recognition-value">{overview?.recognition_rate ?? 0}%</span>
          </div>
          <div className="stats-recognition-track">
            <div
              className="stats-recognition-fill"
              style={{ width: `${Math.min(100, overview?.recognition_rate ?? 0)}%` }}
            />
          </div>
        </div>

        <div className="stats-weak">
          <div className="stats-weak-head">薄弱词 TOP5</div>
          {(words?.weak_words?.length ?? 0) === 0 ? (
            <p className="stats-weak-empty">暂无薄弱词</p>
          ) : (
            <ul className="stats-weak-list">
              {words?.weak_words.map((w) => (
                <li
                  key={w.word}
                  className="stats-weak-item"
                  onClick={() => navigate('/english/words')}
                  title="点击去背单词"
                >
                  <span className="stats-weak-word">{w.word}</span>
                  <span className="stats-weak-forget">忘记 {w.forgotten_count} 次</span>
                  <span className="stats-weak-strength">
                    记忆强度 {Math.round(w.memory_strength)}
                  </span>
                </li>
              ))}
            </ul>
          )}
        </div>
      </section>

      {/* 口语练习详情 */}
      <section className="stats-section">
        <h2 className="stats-section-title">口语练习</h2>
        <div className="stats-speaking-grid">
          <div className="stats-words-cell">
            <span className="stats-words-value">{overview?.speaking_sessions ?? 0}</span>
            <span className="stats-words-label">练习次数</span>
          </div>
          <div className="stats-words-cell">
            <span className="stats-words-value">{overview?.speaking_total_messages ?? 0}</span>
            <span className="stats-words-label">总消息数</span>
          </div>
          <div className="stats-words-cell stats-words-cell-wide">
            <span className="stats-words-value">{formatDateTime(overview?.last_speaking_at ?? null)}</span>
            <span className="stats-words-label">最近练习时间</span>
          </div>
        </div>

        <div className="stats-topics">
          <div className="stats-weak-head">常练话题 TOP5</div>
          {(speaking?.topics?.length ?? 0) === 0 ? (
            <p className="stats-weak-empty">暂无口语练习</p>
          ) : (
            <div className="stats-topic-list">
              {speaking?.topics.map((t) => (
                <div key={t.topic} className="stats-topic-row">
                  <span className="stats-topic-name">{t.topic}</span>
                  <div className="stats-topic-track">
                    <div
                      className="stats-topic-fill"
                      style={{ width: `${(t.count / maxTopic) * 100}%` }}
                    />
                  </div>
                  <span className="stats-topic-count">{t.count} 次</span>
                </div>
              ))}
            </div>
          )}
        </div>
      </section>

      {/* 近 7 天学习趋势 */}
      <section className="stats-section">
        <h2 className="stats-section-title">近 7 天学习趋势</h2>
        <div className="stats-chart-legend">
          {TREND_SEGMENTS.map((s) => (
            <span key={s.key} className="stats-chart-legend-item">
              <span className="stats-chart-dot" style={{ background: s.color }} />
              {s.label}
            </span>
          ))}
        </div>
        <div className="stats-chart">
          {trend.map((t) => {
            const total = t.words_reviewed + t.words_new + t.speaking_messages
            return (
              <div key={t.date} className="stats-chart-col">
                <div className="stats-chart-stack">
                  {TREND_SEGMENTS.map((s) => {
                    const value = t[s.key as TrendKey]
                    if (value <= 0) return null
                    return (
                      <div
                        key={s.key}
                        className="stats-chart-seg"
                        style={{
                          height: `${(value / maxTotal) * 100}%`,
                          background: s.color,
                        }}
                        title={`${s.label}：${value}`}
                      />
                    )
                  })}
                  {total === 0 && <span className="stats-chart-zero">0</span>}
                </div>
                <span className="stats-chart-day">{formatDay(t.date)}</span>
              </div>
            )
          })}
        </div>
      </section>

      {/* AI 动态建议 */}
      <section className="stats-section">
        <div className="stats-section-title-row">
          <h2 className="stats-section-title">AI 导师分析</h2>
          <button
            className="stats-ai-reanalyze"
            onClick={runAnalysis}
            disabled={analysisLoading}
          >
            {analysisLoading ? '分析中...' : '重新分析'}
          </button>
        </div>
        {analysisError && <p className="stats-error">{analysisError}</p>}
        <div className="stats-ai-reply">
          {analysisLoading && !analysis ? (
            <p className="stats-ai-loading">AI 导师正在分析你的学习数据…</p>
          ) : analysis ? (
            <div className="stats-ai-content">{renderBold(analysis)}</div>
          ) : (
            <p className="stats-ai-loading">点击「重新分析」获取学习建议</p>
          )}
        </div>
      </section>

      {/* 外刊精读 */}
      <section className="stats-section">
        <h2 className="stats-section-title">外刊精读</h2>
        <div className="stats-words-row">
          <div className="stats-words-cell">
            <span className="stats-words-value">{overview?.reading_articles_read ?? 0}</span>
            <span className="stats-words-label">已读外刊（篇）</span>
          </div>
        </div>
      </section>
    </div>
  )
}
