import { useEffect, useRef, useState, type MouseEvent as ReactMouseEvent, type ReactNode } from 'react'
import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/AuthContext'
import { getErrorMessage } from '../../api/client'
import {
  collectWord,
  explainText,
  generateArticle,
  getArticle,
  getArticles,
  markRead,
  submitQuiz,
  type QuizSubmitResponse,
  type ReadingArticleDetail,
  type ReadingArticleListItem,
  type ReadingLongSentence,
} from '../../api/reading'
import './Reading.css'

// 难度 / 话题下拉选项
const DIFFICULTIES = ['考研', '四级', '六级']
const TOPICS = ['科技', '经济', '文化', '教育', '社会']

// 生成数量选项
const GEN_COUNTS = [1, 3, 5, 10]

const PAGE_SIZE = 8

// 正文字号：14-22px，默认 16，存 localStorage 记住
const FONT_MIN = 14
const FONT_MAX = 22
const FONT_DEFAULT = 16
const FONT_KEY = 'reading_font_size'

// 长难句解析卡片宽度（用于默认定位到屏幕右侧）
const SENTENCE_CARD_WIDTH = 340

/** ISO 时间 → 'YYYY-MM-DD' */
function formatDate(iso: string): string {
  const t = new Date(iso)
  if (Number.isNaN(t.getTime())) return ''
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${t.getFullYear()}-${pad(t.getMonth() + 1)}-${pad(t.getDate())}`
}

/** 兼容旧数据：字符串长难句 → 对象（无解析） */
function normalizeLongSentence(s: string | ReadingLongSentence): ReadingLongSentence {
  if (typeof s === 'string') return { sentence: s, translation: '', analysis: '' }
  return s
}

/** 在段落文本中高亮命中的长难句，返回混合文本 / 高亮节点 */
function highlightLongSentences(
  text: string,
  longSentences: (string | ReadingLongSentence)[],
  onOpen: (s: ReadingLongSentence) => void,
): ReactNode[] {
  type Range = { start: number; end: number; sentence: ReadingLongSentence }
  const ranges: Range[] = []
  for (const raw of longSentences) {
    const item = normalizeLongSentence(raw)
    const sentence = item.sentence.trim()
    if (!sentence) continue
    let idx = text.indexOf(sentence)
    while (idx !== -1) {
      ranges.push({ start: idx, end: idx + sentence.length, sentence: item })
      idx = text.indexOf(sentence, idx + sentence.length)
    }
  }
  if (ranges.length === 0) return [text]

  ranges.sort((a, b) => a.start - b.start)

  const nodes: ReactNode[] = []
  let cursor = 0
  for (const r of ranges) {
    if (r.start < cursor) continue
    if (r.start > cursor) nodes.push(text.slice(cursor, r.start))
    nodes.push(
      <span
        key={`${r.start}-${r.end}`}
        className="reading-long-sentence"
        onClick={() => onOpen(r.sentence)}
      >
        {r.sentence.sentence}
      </span>,
    )
    cursor = r.end
  }
  if (cursor < text.length) nodes.push(text.slice(cursor))
  return nodes
}

/** 从选区向上找到所在段落文本作为 context */
function getContextSentence(sel: Selection): string {
  let node: Node | null = sel.anchorNode
  while (node) {
    if (node.nodeType === Node.ELEMENT_NODE && (node as Element).tagName === 'P') {
      return (node as Element).textContent?.trim() || ''
    }
    node = node.parentNode
  }
  return sel.toString().trim()
}

interface SelectionState {
  text: string
  context: string
  x: number
  y: number
  isWord: boolean
}

interface ExplainState {
  translation: string
  analysis: string
  x: number
  y: number
}

interface SentenceCardState extends ReadingLongSentence {
  x: number
  y: number
}

/** 外刊精读视图（嵌入英语首页右侧内容区） */
export function ReadingContent() {
  const { user } = useAuth()
  const isAdmin = user?.role === 'admin'
  const navigate = useNavigate()
  // 剩余路径段：'' = 介绍页，'list' = 文章列表，数字 = 文章详情
  const { '*': rest = '' } = useParams()
  const articleId = rest && rest !== 'list' ? Number(rest) : NaN
  // 是否处于详情模式（URL 含合法 articleId）
  const isDetail = Number.isInteger(articleId) && articleId > 0
  // 介绍页 / 文章列表由 URL 路径驱动（介绍 → 列表计入浏览器历史，返回键可回退）
  const view: 'intro' | 'list' = rest === 'list' ? 'list' : 'intro'

  // 列表视图
  const [articles, setArticles] = useState<ReadingArticleListItem[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const [difficulty, setDifficulty] = useState('')
  const [topic, setTopic] = useState('')
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  // 详情视图
  const [article, setArticle] = useState<ReadingArticleDetail | null>(null)
  const [detailLoading, setDetailLoading] = useState(false)

  // 正文字号（localStorage 记住）
  const [fontSize, setFontSize] = useState<number>(() => {
    const saved = Number(localStorage.getItem(FONT_KEY))
    return saved >= FONT_MIN && saved <= FONT_MAX ? saved : FONT_DEFAULT
  })

  // 做题分栏模式
  const [quizMode, setQuizMode] = useState(false)

  // 选中即译（划词）
  const [selection, setSelection] = useState<SelectionState | null>(null)
  const [explain, setExplain] = useState<ExplainState | null>(null)
  const [explainAnchor, setExplainAnchor] = useState<{ x: number; y: number } | null>(null)
  const [explainLoading, setExplainLoading] = useState(false)
  const [explainError, setExplainError] = useState('')

  // 长难句解析卡片（预生成，可拖动）
  const [sentenceCard, setSentenceCard] = useState<SentenceCardState | null>(null)
  const dragOffset = useRef<{ dx: number; dy: number } | null>(null)

  // 做题
  const [answers, setAnswers] = useState<(number | null)[]>([])
  const [quizResult, setQuizResult] = useState<QuizSubmitResponse | null>(null)
  const [quizSubmitting, setQuizSubmitting] = useState(false)

  // 生成文章弹窗
  const [showGenerate, setShowGenerate] = useState(false)
  const [genDifficulty, setGenDifficulty] = useState('考研')
  const [genTopic, setGenTopic] = useState('科技')
  const [genCount, setGenCount] = useState(1)
  const [genProgress, setGenProgress] = useState('')
  const [generating, setGenerating] = useState(false)

  // 提示 + 标记已读
  const [toast, setToast] = useState('')
  const [markingRead, setMarkingRead] = useState(false)

  const toastTimer = useRef<number | null>(null)

  const showToast = (msg: string) => {
    setToast(msg)
    if (toastTimer.current) window.clearTimeout(toastTimer.current)
    toastTimer.current = window.setTimeout(() => setToast(''), 2500)
  }

  /** 调整正文字号并写入 localStorage */
  const changeFontSize = (delta: number) => {
    setFontSize((prev) => {
      const next = Math.min(FONT_MAX, Math.max(FONT_MIN, prev + delta))
      localStorage.setItem(FONT_KEY, String(next))
      return next
    })
  }

  /** 打开长难句解析卡片（预生成数据，默认定位屏幕右侧） */
  const openSentenceCard = (s: ReadingLongSentence) => {
    setSentenceCard({
      sentence: s.sentence,
      translation: s.translation,
      analysis: s.analysis,
      x: Math.max(16, window.innerWidth - SENTENCE_CARD_WIDTH - 24),
      y: 120,
    })
  }

  // 卡片拖动：mousedown 记录偏移，mousemove 更新位置，mouseup 解除
  const onSentenceCardDrag = (e: globalThis.MouseEvent) => {
    const off = dragOffset.current
    if (!off) return
    setSentenceCard((prev) =>
      prev ? { ...prev, x: e.clientX - off.dx, y: e.clientY - off.dy } : prev,
    )
  }

  const stopSentenceCardDrag = () => {
    dragOffset.current = null
    document.removeEventListener('mousemove', onSentenceCardDrag)
    document.removeEventListener('mouseup', stopSentenceCardDrag)
  }

  const startSentenceCardDrag = (e: ReactMouseEvent) => {
    if (!sentenceCard) return
    e.preventDefault() // 拖动时不触发文本选择
    dragOffset.current = {
      dx: e.clientX - sentenceCard.x,
      dy: e.clientY - sentenceCard.y,
    }
    document.addEventListener('mousemove', onSentenceCardDrag)
    document.addEventListener('mouseup', stopSentenceCardDrag)
  }

  // 卸载时清理拖动监听
  useEffect(() => {
    return () => {
      document.removeEventListener('mousemove', onSentenceCardDrag)
      document.removeEventListener('mouseup', stopSentenceCardDrag)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  /** 拉取文章列表 */
  const loadList = async (p = page, d = difficulty, t = topic) => {
    setLoading(true)
    setError('')
    try {
      const res = await getArticles({ page: p, size: PAGE_SIZE, difficulty: d || undefined, topic: t || undefined })
      setArticles(res.data.items)
      setTotal(res.data.total)
      setPage(res.data.page)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  /** 加载文章详情（由 URL 的 articleId 参数触发） */
  const loadArticle = async (id: number) => {
    setDetailLoading(true)
    setError('')
    setArticle(null)
    setSelection(null)
    setExplain(null)
    setSentenceCard(null)
    setQuizResult(null)
    setQuizMode(false)
    try {
      const res = await getArticle(id)
      setArticle(res.data)
      setAnswers(Array(res.data.quiz.length).fill(null))
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setDetailLoading(false)
    }
  }

  /** 打开文章详情：写入 URL 路径，浏览器历史记录「列表 → 详情」 */
  const openArticle = (id: number) => {
    navigate(`/english/reading/${id}`)
  }

  // 首次进入加载列表
  useEffect(() => {
    void loadList(1, '', '')
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 根据 URL 路径中的 articleId 加载详情 / 回到列表（含浏览器前进后退）
  useEffect(() => {
    if (Number.isInteger(articleId) && articleId > 0) {
      void loadArticle(articleId)
    } else {
      setArticle(null)
      setSelection(null)
      setExplain(null)
      setSentenceCard(null)
      setQuizResult(null)
      setQuizMode(false)
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [articleId])

  // 点击文档空白处关闭选中工具栏
  useEffect(() => {
    const onDocMouseDown = (e: MouseEvent) => {
      const target = e.target as HTMLElement
      if (target.closest('.reading-toolbar') || target.closest('.reading-explain') || target.closest('.reading-sentence-card')) return
      setSelection(null)
    }
    document.addEventListener('mousedown', onDocMouseDown)
    return () => document.removeEventListener('mousedown', onDocMouseDown)
  }, [])

  /** 正文选中（划词） */
  const handleMouseUp = () => {
    const sel = window.getSelection()
    if (!sel || sel.rangeCount === 0 || sel.isCollapsed) return
    const text = sel.toString().trim()
    if (!text) return
    const rect = sel.getRangeAt(0).getBoundingClientRect()
    setSelection({
      text,
      context: getContextSentence(sel),
      x: Math.min(Math.max(rect.left + rect.width / 2, 100), window.innerWidth - 100),
      y: rect.top - 10,
      isWord: !/\s/.test(text),
    })
  }

  /** 翻译并解析选中的词 / 句子（划词即译，实时调 AI） */
  const doExplain = async (text: string, context: string, rect?: DOMRect) => {
    const anchor = rect
      ? { x: rect.left, y: rect.bottom + 6 }
      : { x: selection?.x ?? 200, y: (selection?.y ?? 200) + 24 }
    setExplainAnchor(anchor)
    setExplain(null)
    setExplainLoading(true)
    setExplainError('')
    try {
      const res = await explainText(text, context)
      setExplain({
        translation: res.data.translation,
        analysis: res.data.analysis,
        x: anchor.x,
        y: anchor.y,
      })
    } catch (err) {
      setExplainError(getErrorMessage(err))
    } finally {
      setExplainLoading(false)
    }
  }

  /** 收集生词 */
  const handleCollect = async (word: string) => {
    if (!article) return
    try {
      const res = await collectWord(article.id, word)
      showToast(`已加入生词本：${res.data.word}`)
    } catch (err) {
      showToast(getErrorMessage(err))
    }
  }

  /** 标记已读 */
  const handleMarkRead = async () => {
    if (!article) return
    setMarkingRead(true)
    try {
      await markRead(article.id)
      setArticle((prev) =>
        prev
          ? {
              ...prev,
              history: {
                read_at: new Date().toISOString(),
                quiz_score: prev.history?.quiz_score ?? null,
                words_collected: prev.history?.words_collected ?? 0,
              },
            }
          : prev,
      )
      showToast('已标记已读')
    } catch (err) {
      showToast(getErrorMessage(err))
    } finally {
      setMarkingRead(false)
    }
  }

  /** 做题：选择选项 */
  const selectAnswer = (qi: number, oi: number) => {
    if (quizResult) return
    setAnswers((prev) => prev.map((a, i) => (i === qi ? oi : a)))
  }

  /** 提交做题 */
  const handleSubmitQuiz = async () => {
    if (!article) return
    setQuizSubmitting(true)
    setError('')
    try {
      const res = await submitQuiz(
        article.id,
        answers.map((a) => (a == null ? -1 : a)),
      )
      setQuizResult(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setQuizSubmitting(false)
    }
  }

  /** 生成文章（逐篇请求以显示进度，一篇失败不影响其他篇） */
  const handleGenerate = async () => {
    setGenerating(true)
    setGenProgress('')
    setError('')

    let success = 0
    let failed = 0
    let firstId: number | null = null

    for (let i = 0; i < genCount; i++) {
      setGenProgress(genCount > 1 ? `正在生成第${i + 1}/${genCount}篇...` : '')
      try {
        const res = await generateArticle(genDifficulty, genTopic, 1)
        const item = res.data.generated[0]
        if (item) {
          if (firstId == null) firstId = item.id
          success += 1
        } else {
          failed += 1
        }
      } catch {
        failed += 1
      }
    }

    setShowGenerate(false)
    setGenProgress('')
    setDifficulty('')
    setTopic('')

    if (success > 0) {
      showToast(failed > 0 ? `成功生成${success}篇文章，${failed}篇失败` : `成功生成${success}篇文章`)
      void loadList(1, '', '')
      // 单篇：保持原有行为，直接打开生成的文章
      if (genCount === 1 && firstId != null) void openArticle(firstId)
    } else {
      showToast('生成失败，请重试')
    }

    setGenerating(false)
  }

  const totalPages = Math.max(1, Math.ceil(total / PAGE_SIZE))

  // 生成文章弹窗（介绍页与列表页共用）
  const generateModal = showGenerate ? (
    <div className="reading-modal-mask" onClick={() => { if (!generating) setShowGenerate(false) }}>
      <div className="reading-modal" onClick={(e) => e.stopPropagation()}>
        <h3>AI 生成外刊文章</h3>
        <label className="reading-modal-label">难度</label>
        <select
          className="reading-select"
          value={genDifficulty}
          onChange={(e) => setGenDifficulty(e.target.value)}
          disabled={generating}
        >
          {DIFFICULTIES.map((d) => (
            <option key={d} value={d}>{d}</option>
          ))}
        </select>
        <label className="reading-modal-label">话题</label>
        <select
          className="reading-select"
          value={genTopic}
          onChange={(e) => setGenTopic(e.target.value)}
          disabled={generating}
        >
          {TOPICS.map((t) => (
            <option key={t} value={t}>{t}</option>
          ))}
        </select>
        <label className="reading-modal-label">生成数量</label>
        <select
          className="reading-select"
          value={genCount}
          onChange={(e) => setGenCount(Number(e.target.value))}
          disabled={generating}
        >
          {GEN_COUNTS.map((c) => (
            <option key={c} value={c}>{c} 篇</option>
          ))}
        </select>
        <div className="reading-modal-actions">
          <button className="reading-modal-cancel" onClick={() => setShowGenerate(false)} disabled={generating}>
            取消
          </button>
          <button className="reading-modal-confirm" onClick={() => void handleGenerate()} disabled={generating}>
            {generating ? (genProgress || '生成中...') : genCount > 1 ? `开始生成（共${genCount}篇）` : '开始生成'}
          </button>
        </div>
      </div>
    </div>
  ) : null

  // ---------- 介绍页 ----------
  if (!isDetail && view === 'intro') {
    return (
      <div className="reading-intro">
        <h2 className="english-content-title">外刊精读</h2>
        <span className="english-content-accent" aria-hidden="true" />
        <p className="english-content-intro">精选外刊文章，长难句解析，边读边积累</p>

        <div className="english-detail-card">
          <section className="english-detail-section">
            <h3 className="english-detail-heading">学习方法</h3>
            <ul className="english-detail-list">
              <li>AI 模仿《经济学人》风格生成考研 / 四六级外刊文章，每篇 350-450 词</li>
              <li>长难句自动高亮，点击查看中文翻译和语法结构分析</li>
              <li>选中任意单词或句子，即时翻译和用法解析</li>
              <li>读完后 AI 出题检验理解，左右分栏对照原文做题</li>
              <li>生词一键加入背单词本，自动进入复习队列</li>
            </ul>
          </section>
          <section className="english-detail-section">
            <h3 className="english-detail-heading">使用说明</h3>
            <ul className="english-detail-list">
              <li>点击「开始阅读」进入文章列表</li>
              <li>按难度和话题筛选文章，点击开始精读</li>
              <li>字体大小可调，长难句解析卡片可拖动</li>
              <li>阅读数据自动同步到学习数据页</li>
            </ul>
          </section>
        </div>

        {isAdmin && (
          <button className="reading-generate-btn" onClick={() => setShowGenerate(true)}>
            ✨ AI 生成新文章
          </button>
        )}

        <button
          className="english-start-btn"
          onClick={() => navigate('/english/reading/list')}
        >
          开始阅读
        </button>

        {generateModal}
        {toast && <div className="reading-toast">{toast}</div>}
      </div>
    )
  }

  // ---------- 列表视图 ----------
  if (!isDetail) {
    return (
      <div className="reading-container">
        <header className="reading-header">
          <div className="reading-header-title-row">
            <div>
              <h2 className="reading-title">外刊精读</h2>
              <span className="reading-title-accent" aria-hidden="true" />
              <p className="reading-subtitle">精选外刊文章，长难句解析，边读边积累</p>
            </div>
            {isAdmin && (
              <button className="reading-generate-btn" onClick={() => setShowGenerate(true)}>
                ✨ AI 生成新文章
              </button>
            )}
          </div>

          <div className="reading-filters">
            <select
              className="reading-select"
              value={difficulty}
              onChange={(e) => {
                setDifficulty(e.target.value)
                void loadList(1, e.target.value, topic)
              }}
            >
              <option value="">全部难度</option>
              {DIFFICULTIES.map((d) => (
                <option key={d} value={d}>{d}</option>
              ))}
            </select>
            <select
              className="reading-select"
              value={topic}
              onChange={(e) => {
                setTopic(e.target.value)
                void loadList(1, difficulty, e.target.value)
              }}
            >
              <option value="">全部话题</option>
              {TOPICS.map((t) => (
                <option key={t} value={t}>{t}</option>
              ))}
            </select>
          </div>
        </header>

        {error && <p className="reading-error">{error}</p>}

        {loading ? (
          <div className="reading-loading">加载中...</div>
        ) : articles.length === 0 ? (
          <div className="reading-empty">
            <span aria-hidden="true">📚</span>
            <p>暂无文章{isAdmin ? '，点击右上角「AI 生成新文章」' : ''}</p>
          </div>
        ) : (
          <>
            <div className="reading-grid">
              {articles.map((a) => (
                <button key={a.id} className="reading-card" onClick={() => void openArticle(a.id)}>
                  <div className="reading-card-top">
                    <span className="reading-card-tag">{a.difficulty}</span>
                    {a.is_read && <span className="reading-card-read">已读</span>}
                  </div>
                  <h3 className="reading-card-title">{a.title}</h3>
                  <div className="reading-card-meta">
                    <span>#{a.topic}</span>
                    <span>{a.word_count} 词</span>
                    <span>{formatDate(a.created_at)}</span>
                  </div>
                </button>
              ))}
            </div>

            {totalPages > 1 && (
              <div className="reading-pagination">
                <button
                  className="reading-page-btn"
                  disabled={page <= 1}
                  onClick={() => void loadList(page - 1, difficulty, topic)}
                >
                  上一页
                </button>
                <span className="reading-page-info">{page} / {totalPages}</span>
                <button
                  className="reading-page-btn"
                  disabled={page >= totalPages}
                  onClick={() => void loadList(page + 1, difficulty, topic)}
                >
                  下一页
                </button>
              </div>
            )}
          </>
        )}

        {generateModal}

        {toast && <div className="reading-toast">{toast}</div>}
      </div>
    )
  }

  // ---------- 详情视图 ----------
  if (detailLoading || !article) {
    return <div className="reading-loading">加载中...</div>
  }

  const longSentences = (article.long_sentences ?? []).map(normalizeLongSentence)
  const contentParagraphs = article.content.replace(/\r\n/g, '\n').split(/\n{2,}/).filter((p) => p.trim())

  const isRead = !!article.history?.read_at
  const totalQuestions = article.quiz.length
  // 上次得分：本次判分用 correct/total；历史分数为百分比，反推答对题数
  const lastCorrect =
    quizResult != null
      ? quizResult.correct
      : article.history?.quiz_score != null
        ? Math.round((article.history.quiz_score / 100) * totalQuestions)
        : null

  // 正文（含长难句高亮），字号由 fontSize 控制，行高随字号自适应
  const articleBody = (
    <div className="reading-article-body" style={{ fontSize }} onMouseUp={handleMouseUp}>
      {contentParagraphs.map((para, pi) => (
        <p key={pi} className="reading-paragraph">
          {highlightLongSentences(para, longSentences, openSentenceCard)}
        </p>
      ))}
    </div>
  )

  // 题目内容（右侧栏）
  const quizBody = (
    <div className="reading-quiz-pane-body">
      {article.quiz.length === 0 ? (
        <p className="reading-quiz-empty">该文章暂无配套题目</p>
      ) : (
        <>
          {article.quiz.map((q, qi) => {
            const result = quizResult?.results[qi]
            return (
              <div key={qi} className="reading-quiz-item">
                <p className="reading-quiz-question">{qi + 1}. {q.question}</p>
                <div className="reading-quiz-options">
                  {q.options.map((opt, oi) => {
                    const selected = answers[qi] === oi
                    const isCorrect = result && oi === result.correct_answer
                    const isWrongSelected = result && selected && oi !== result.correct_answer
                    let cls = 'reading-quiz-option'
                    if (!result && selected) cls += ' reading-quiz-option-selected'
                    if (isCorrect) cls += ' reading-quiz-option-correct'
                    if (isWrongSelected) cls += ' reading-quiz-option-wrong'
                    return (
                      <button
                        key={oi}
                        className={cls}
                        disabled={!!result}
                        onClick={() => selectAnswer(qi, oi)}
                      >
                        <span className="reading-quiz-option-key">{String.fromCharCode(65 + oi)}</span>
                        <span>{opt}</span>
                      </button>
                    )
                  })}
                </div>
                {result && (
                  <div className={`reading-quiz-explain ${result.is_correct ? 'is-correct' : 'is-wrong'}`}>
                    <span className="reading-quiz-explain-verdict">
                      {result.is_correct ? '✅ 正确' : '❌ 错误'}
                      {result.your_answer == null || result.your_answer < 0 ? '（未作答）' : ''}
                    </span>
                    <span className="reading-quiz-explain-text">{result.explanation}</span>
                  </div>
                )}
              </div>
            )
          })}
          {!quizResult && (
            <button className="reading-submit-btn" onClick={() => void handleSubmitQuiz()} disabled={quizSubmitting}>
              {quizSubmitting ? '判分中...' : '提交答案'}
            </button>
          )}
          {quizResult && (
            <div className="reading-quiz-score">
              本次得分：<strong>{quizResult.score}</strong> 分（{quizResult.correct} / {quizResult.total}）
            </div>
          )}
        </>
      )}
    </div>
  )

  return (
    <div className={`reading-container reading-detail${quizMode ? ' reading-detail-split' : ''}`}>
      <header className="reading-detail-header">
        <h2 className="reading-detail-title">{article.title}</h2>
        <div className="reading-detail-toolbar">
          <div className="reading-detail-meta">
            <span className="reading-card-tag">{article.difficulty}</span>
            <span className="reading-detail-meta-item">#{article.topic}</span>
            <span className="reading-detail-meta-item">{article.word_count} 词</span>
          </div>
          <div className="reading-detail-actions">
            <div className="reading-font-group">
              <button className="reading-font-btn" onClick={() => changeFontSize(-1)} title="减小字号">A-</button>
              <button className="reading-font-btn" onClick={() => changeFontSize(1)} title="增大字号">A+</button>
            </div>
            <button
              className={isRead ? 'reading-btn reading-btn-done' : 'reading-btn'}
              onClick={isRead ? undefined : () => void handleMarkRead()}
              disabled={markingRead || isRead}
            >
              {isRead ? '已读' : markingRead ? '标记中...' : '标记已读'}
            </button>
            {!quizMode && (
              <button
                className="reading-btn reading-btn-primary"
                onClick={() => setQuizMode(true)}
                disabled={totalQuestions === 0}
              >
                开始做题
              </button>
            )}
            {lastCorrect != null && totalQuestions > 0 && (
              <span className="reading-detail-score">上次得分 {lastCorrect}/{totalQuestions}</span>
            )}
          </div>
        </div>
      </header>

      {quizMode ? (
        <div className="reading-split">
          <div className="reading-split-left">{articleBody}</div>
          <div className="reading-split-right">
            <div className="reading-quiz-pane-head">
              <span className="reading-quiz-pane-title">阅读理解</span>
              <button className="reading-quiz-exit" onClick={() => setQuizMode(false)}>退出做题</button>
            </div>
            {quizBody}
          </div>
        </div>
      ) : (
        <div className="reading-article">{articleBody}</div>
      )}

      {/* 划词工具条 */}
      {selection && (
        <div
          className="reading-toolbar"
          style={{ left: selection.x, top: selection.y }}
          onMouseDown={(e) => e.preventDefault()}
        >
          <button
            className="reading-toolbar-btn"
            onClick={() => void doExplain(selection.text, selection.context)}
          >
            🔍 翻译
          </button>
          {selection.isWord && (
            <button
              className="reading-toolbar-btn reading-toolbar-btn-collect"
              onClick={() => void handleCollect(selection.text)}
            >
              ➕ 生词本
            </button>
          )}
        </div>
      )}

      {/* 划词解析结果 */}
      {explainLoading && (
        <div
          className="reading-explain reading-explain-loading"
          style={{ left: explainAnchor?.x, top: explainAnchor?.y }}
        >
          解析中...
        </div>
      )}
      {explainError && (
        <div
          className="reading-explain reading-explain-error"
          style={{ left: explainAnchor?.x, top: explainAnchor?.y }}
        >
          {explainError}
        </div>
      )}
      {explain && !explainLoading && (
        <div className="reading-explain" style={{ left: explain.x, top: explain.y }}>
          <button className="reading-explain-close" onClick={() => setExplain(null)}>×</button>
          <div className="reading-explain-section">
            <div className="reading-explain-label">翻译</div>
            <div className="reading-explain-text">{explain.translation}</div>
          </div>
          {explain.analysis && (
            <div className="reading-explain-section">
              <div className="reading-explain-label">解析</div>
              <div className="reading-explain-text">{explain.analysis}</div>
            </div>
          )}
        </div>
      )}

      {/* 长难句解析卡片（预生成，可拖动） */}
      {sentenceCard && (
        <div
          className="reading-sentence-card"
          style={{ left: sentenceCard.x, top: sentenceCard.y, fontSize }}
        >
          <div className="reading-sentence-card-bar" onMouseDown={startSentenceCardDrag}>
            <span className="reading-sentence-card-bar-title">长难句解析</span>
            <button className="reading-sentence-card-close" onClick={() => setSentenceCard(null)}>×</button>
          </div>
          <div className="reading-sentence-card-body">
            <p className="reading-sentence-card-sentence">{sentenceCard.sentence}</p>
            {sentenceCard.translation && (
              <div className="reading-sentence-card-section">
                <div className="reading-sentence-card-label">翻译</div>
                <div className="reading-sentence-card-text">{sentenceCard.translation}</div>
              </div>
            )}
            {sentenceCard.analysis && (
              <div className="reading-sentence-card-section">
                <div className="reading-sentence-card-label">解析</div>
                <div className="reading-sentence-card-text">{sentenceCard.analysis}</div>
              </div>
            )}
          </div>
        </div>
      )}

      {toast && <div className="reading-toast">{toast}</div>}
    </div>
  )
}
