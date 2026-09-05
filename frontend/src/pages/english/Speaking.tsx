import {
  useEffect,
  useRef,
  useState,
  type KeyboardEvent,
  type MouseEvent,
} from 'react'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import { getErrorMessage } from '../../api/client'
import {
  createConversation,
  deleteConversation,
  getConversation,
  getConversations,
  getTtsUrl,
  sendMessage,
  type ConversationSummary,
  type Level,
  type SpeakingSuggestion,
  type Topic,
} from '../../api/english'
import './Speaking.css'

/** 页面内的一条消息（system 用于本地提示，不带翻译、不入库） */
interface Message {
  id: number
  role: 'user' | 'assistant' | 'system'
  content: string
  translation?: string
}

/** 生成本地消息唯一 id（仅用于前端播放状态定位） */
let messageSeq = 0
function genMessageId(): number {
  messageSeq += 1
  return messageSeq
}

/** 语速选项（倍速） */
const RATES = [0.5, 0.75, 1, 1.25, 1.5]

/** 话题选项 */
const TOPICS: { id: Topic; label: string }[] = [
  { id: 'daily', label: '日常对话' },
  { id: 'interview', label: '面试' },
  { id: 'travel', label: '旅游' },
  { id: 'campus', label: '校园' },
]

/** 难度选项 */
const LEVELS: { id: Level; label: string }[] = [
  { id: 'beginner', label: '初级' },
  { id: 'intermediate', label: '中级' },
  { id: 'advanced', label: '高级' },
]

function topicLabel(id: Topic): string {
  return TOPICS.find((t) => t.id === id)?.label ?? id
}

function levelLabel(id: Level): string {
  return LEVELS.find((l) => l.id === id)?.label ?? id
}

/** 欢迎提示（本地 system 消息） */
function welcomeMessage(topic: Topic, level: Level): Message {
  return {
    id: genMessageId(),
    role: 'system',
    content: `欢迎来到口语练习！当前话题：${topicLabel(topic)}，难度：${levelLabel(level)}。用英语输入开始对话吧。`,
  }
}

/** 对话标题：前 20 字，超出加省略号（与后端一致） */
function makeTitle(content: string): string {
  const t = content.trim()
  return t.length > 20 ? `${t.slice(0, 20)}...` : t
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

/** 英语口语练习：AI 对话 + 翻译 + 辅助功能 三栏布局 */
export default function Speaking() {
  const { user, logout } = useAuth()

  const [conversations, setConversations] = useState<ConversationSummary[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([
    { id: genMessageId(), role: 'system', content: '加载中...' },
  ])
  const [topic, setTopic] = useState<Topic>('daily')
  const [level, setLevel] = useState<Level>('beginner')
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<SpeakingSuggestion[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')
  const [historyOpen, setHistoryOpen] = useState(true)

  // TTS 语音朗读相关状态
  const [currentPlayingId, setCurrentPlayingId] = useState<number | null>(null)
  const [isPlaying, setIsPlaying] = useState(false)
  const [autoPlay, setAutoPlay] = useState(
    () => localStorage.getItem('speaking_autoplay') === '1',
  )
  const [playRate, setPlayRate] = useState(() => {
    const saved = Number(localStorage.getItem('speaking_rate'))
    return RATES.includes(saved) ? saved : 1
  })

  // 用于自动滚动到最新消息
  const chatListRef = useRef<HTMLDivElement>(null)
  const translationListRef = useRef<HTMLDivElement>(null)
  // 防止 React StrictMode 下初始化逻辑重复执行
  const initializedRef = useRef(false)
  // 全局 Audio 对象（复用一个实例，切换 src 即停止上一段播放）
  const audioRef = useRef<HTMLAudioElement | null>(null)

  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight
    }
    if (translationListRef.current) {
      translationListRef.current.scrollTop = translationListRef.current.scrollHeight
    }
  }, [messages])

  /** 获取（懒创建）全局 Audio 实例 */
  function getAudio(): HTMLAudioElement {
    if (!audioRef.current) {
      const audio = new Audio()
      audio.onended = () => {
        setCurrentPlayingId(null)
        setIsPlaying(false)
      }
      audio.onerror = () => {
        setCurrentPlayingId(null)
        setIsPlaying(false)
      }
      audioRef.current = audio
    }
    return audioRef.current
  }

  /** 停止当前播放并清空状态 */
  function stopAudio() {
    const audio = audioRef.current
    if (audio) {
      audio.pause()
      audio.currentTime = 0
    }
    setCurrentPlayingId(null)
    setIsPlaying(false)
  }

  /** 朗读某条消息：若正在播放同一条则停止，否则停止旧播放并播放新的 */
  function playMessage(msg: Message) {
    if (currentPlayingId === msg.id && isPlaying) {
      stopAudio()
      return
    }
    const audio = getAudio()
    audio.src = getTtsUrl(msg.content, playRate)
    audio.play().catch(() => {
      setCurrentPlayingId(null)
      setIsPlaying(false)
    })
    setCurrentPlayingId(msg.id)
    setIsPlaying(true)
  }

  // 卸载时停止播放并释放音频
  useEffect(() => {
    return () => {
      if (audioRef.current) {
        audioRef.current.pause()
        audioRef.current.src = ''
      }
    }
  }, [])

  /** 加载指定对话的详情（消息、话题、难度） */
  const loadConversation = async (id: number) => {
    stopAudio()
    const res = await getConversation(id)
    const detail = res.data
    setCurrentId(detail.id)
    setTopic(detail.topic)
    setLevel(detail.level)
    const loaded: Message[] = detail.messages.map((m) => ({
      id: genMessageId(),
      role: m.role,
      content: m.content,
      translation: m.translation,
    }))
    setMessages(
      loaded.length > 0 ? loaded : [welcomeMessage(detail.topic, detail.level)],
    )
    setSuggestions([])
    setInput('')
    setError('')
  }

  /** 重新拉取对话列表 */
  const refreshConversations = async () => {
    const res = await getConversations()
    setConversations(res.data)
  }

  /** 新建对话：用当前选中的话题 / 难度 */
  const handleNewConversation = async () => {
    stopAudio()
    try {
      const res = await createConversation(topic, level)
      setCurrentId(res.data.id)
      setMessages([welcomeMessage(topic, level)])
      setSuggestions([])
      setInput('')
      setError('')
      await refreshConversations()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 切换对话 */
  const handleSelectConversation = async (id: number) => {
    if (id === currentId) return
    try {
      await loadConversation(id)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 删除对话 */
  const handleDeleteConversation = async (
    id: number,
    e: MouseEvent<HTMLButtonElement>,
  ) => {
    e.stopPropagation()
    try {
      await deleteConversation(id)
      const remaining = conversations.filter((c) => c.id !== id)
      setConversations(remaining)
      if (id === currentId) {
        if (remaining.length > 0) {
          await loadConversation(remaining[0].id)
        } else {
          await handleNewConversation()
        }
      }
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 发送消息（有状态接口，自动保存到当前对话） */
  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending || currentId == null) return

    const userMsg: Message = {
      id: genMessageId(),
      role: 'user',
      content: text,
      translation: '',
    }
    const nextMessages = [...messages, userMsg]
    const isFirstUserMessage = !messages.some((m) => m.role === 'user')

    setMessages(nextMessages)
    setInput('')
    setSending(true)
    setError('')

    try {
      const res = await sendMessage(currentId, text)
      const { ai_reply, translation, user_translation, suggestions: next } = res.data

      // 回填用户消息的中文翻译，并追加 AI 回复
      const updated = nextMessages.map((m) =>
        m === userMsg ? { ...m, translation: user_translation } : m,
      )
      const aiMsg: Message = {
        id: genMessageId(),
        role: 'assistant',
        content: ai_reply,
        translation,
      }
      updated.push(aiMsg)
      setMessages(updated)
      setSuggestions(next)

      // 自动朗读：开关开启时自动播放本次 AI 回复
      if (autoPlay) {
        playMessage(aiMsg)
      }

      // 更新列表里的标题与时间，并置顶
      setConversations((prev) => {
        const updatedList = prev.map((c) =>
          c.id === currentId
            ? {
                ...c,
                title: isFirstUserMessage ? makeTitle(text) : c.title,
                updated_at: new Date().toISOString(),
              }
            : c,
        )
        return updatedList.sort(
          (a, b) => new Date(b.updated_at).getTime() - new Date(a.updated_at).getTime(),
        )
      })
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  /** Ctrl+Enter / Cmd+Enter 发送 */
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && (e.ctrlKey || e.metaKey)) {
      e.preventDefault()
      handleSend()
    }
  }

  /** 选择话题（用于下次「新建对话」，不影响当前对话） */
  const handleTopicChange = (t: Topic) => {
    setTopic(t)
  }

  /** 选择难度 */
  const handleLevelChange = (l: Level) => {
    setLevel(l)
  }

  /** 点击推荐句子，填入输入框 */
  const handleSuggestionClick = (s: SpeakingSuggestion) => {
    setInput(s.en)
  }

  /** 切换自动朗读开关并持久化到 localStorage */
  const handleToggleAutoPlay = () => {
    setAutoPlay((prev) => {
      const next = !prev
      localStorage.setItem('speaking_autoplay', next ? '1' : '0')
      return next
    })
  }

  /** 切换语速并持久化到 localStorage */
  const handleRateChange = (r: number) => {
    setPlayRate(r)
    localStorage.setItem('speaking_rate', String(r))
  }

  // 初始化：拉取对话列表，有则加载最近一条，无则新建
  useEffect(() => {
    if (initializedRef.current) return
    initializedRef.current = true
    ;(async () => {
      try {
        const res = await getConversations()
        const list = res.data
        setConversations(list)
        if (list.length > 0) {
          await loadConversation(list[0].id)
        } else {
          await handleNewConversation()
        }
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  // 翻译列展示的消息（排除 system 提示）
  const translationMessages = messages.filter((m) => m.role !== 'system')

  return (
    <div className="speaking-page">
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

      <div className="speaking-layout">
        <div className="speaking-cards">
          {/* 左栏：AI 对话 */}
          <section className="speaking-col speaking-chat">
            <header className="speaking-col-header">AI 对话</header>

            {/* 历史对话区 */}
            <div className="speaking-history">
              <div className="speaking-history-bar">
                <button className="speaking-new-btn" onClick={handleNewConversation}>
                  + 新建对话
                </button>
                <button
                  className="speaking-history-toggle"
                  onClick={() => setHistoryOpen((v) => !v)}
                >
                  历史对话 {historyOpen ? '▾' : '▸'}
                </button>
              </div>
              {historyOpen && (
                <div className="speaking-history-list">
                  {conversations.length === 0 ? (
                    <p className="speaking-history-empty">暂无历史对话</p>
                  ) : (
                    conversations.map((c) => (
                      <div
                        key={c.id}
                        className={
                          c.id === currentId
                            ? 'speaking-history-item speaking-history-item-active'
                            : 'speaking-history-item'
                        }
                        onClick={() => handleSelectConversation(c.id)}
                      >
                        <div className="speaking-history-info">
                          <span className="speaking-history-title">{c.title}</span>
                          <span className="speaking-history-time">
                            {formatRelativeTime(c.updated_at)}
                          </span>
                        </div>
                        <button
                          className="speaking-history-delete"
                          onClick={(e) => handleDeleteConversation(c.id, e)}
                        >
                          删除
                        </button>
                      </div>
                    ))
                  )}
                </div>
              )}
            </div>

            <div className="speaking-chat-list" ref={chatListRef}>
              {messages.map((m) => (
                <div key={m.id} className={`speaking-msg speaking-msg-${m.role}`}>
                  {m.role !== 'system' && (
                    <span className="speaking-msg-role">
                      {m.role === 'user' ? '你' : 'AI'}
                    </span>
                  )}
                  {m.role === 'assistant' ? (
                    <div className="speaking-bubble-row">
                      <div className="speaking-bubble">{m.content}</div>
                      <button
                        className={
                          currentPlayingId === m.id && isPlaying
                            ? 'speaking-play-btn speaking-play-btn-active'
                            : 'speaking-play-btn'
                        }
                        onClick={() => playMessage(m)}
                        title={currentPlayingId === m.id && isPlaying ? '停止朗读' : '朗读'}
                        aria-label={currentPlayingId === m.id && isPlaying ? '停止朗读' : '朗读'}
                      >
                        {currentPlayingId === m.id && isPlaying ? '⏸' : '🔊'}
                      </button>
                    </div>
                  ) : (
                    <div className="speaking-bubble">{m.content}</div>
                  )}
                </div>
              ))}
            </div>

            <div className="speaking-chat-input">
              <textarea
                className="speaking-textarea"
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="用英语输入你想说的话..."
              />
              {error && <p className="speaking-error">{error}</p>}
              <button
                className="speaking-send-btn"
                onClick={handleSend}
                disabled={sending || currentId == null}
              >
                {sending ? '发送中...' : '发送'}
              </button>
            </div>
          </section>

          {/* 中栏：翻译 */}
          <section className="speaking-col speaking-translation">
            <header className="speaking-col-header">翻译</header>

            <div className="speaking-translation-list" ref={translationListRef}>
              {translationMessages.map((m, i) => (
                <div key={i} className={`speaking-trans-msg speaking-trans-${m.role}`}>
                  <div className="speaking-trans-bubble">{m.translation ?? ''}</div>
                </div>
              ))}
            </div>
          </section>

          {/* 右栏：辅助功能 */}
          <section className="speaking-col speaking-tools">
            <header className="speaking-col-header">辅助功能</header>

            <div className="speaking-tools-content">
              {/* 话题选择 */}
              <div className="speaking-tool-block">
                <p className="speaking-tool-label">选择话题</p>
                <div className="speaking-tool-buttons">
                  {TOPICS.map((t) => (
                    <button
                      key={t.id}
                      className={
                        t.id === topic
                          ? 'speaking-tool-btn speaking-tool-btn-active'
                          : 'speaking-tool-btn'
                      }
                      onClick={() => handleTopicChange(t.id)}
                    >
                      {t.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 难度选择 */}
              <div className="speaking-tool-block">
                <p className="speaking-tool-label">选择难度</p>
                <div className="speaking-tool-buttons">
                  {LEVELS.map((l) => (
                    <button
                      key={l.id}
                      className={
                        l.id === level
                          ? 'speaking-tool-btn speaking-tool-btn-active'
                          : 'speaking-tool-btn'
                      }
                      onClick={() => handleLevelChange(l.id)}
                    >
                      {l.label}
                    </button>
                  ))}
                </div>
              </div>

              {/* 朗读设置 */}
              <div className="speaking-tool-block">
                <p className="speaking-tool-label">朗读设置</p>
                <div className="speaking-autoplay-row">
                  <span className="speaking-autoplay-label">自动朗读 AI 回复</span>
                  <button
                    className={autoPlay ? 'speaking-toggle speaking-toggle-on' : 'speaking-toggle'}
                    onClick={handleToggleAutoPlay}
                    role="switch"
                    aria-checked={autoPlay}
                  >
                    <span className="speaking-toggle-knob" />
                  </button>
                </div>
                <div className="speaking-rate-row">
                  <span className="speaking-rate-label">语速</span>
                  <div className="speaking-rate-buttons">
                    {RATES.map((r) => (
                      <button
                        key={r}
                        className={
                          r === playRate
                            ? 'speaking-rate-btn speaking-rate-btn-active'
                            : 'speaking-rate-btn'
                        }
                        onClick={() => handleRateChange(r)}
                      >
                        {r}x
                      </button>
                    ))}
                  </div>
                </div>
              </div>

              {/* 推荐回复 */}
              <div className="speaking-tool-block">
                <p className="speaking-tool-label">推荐回复</p>
                {suggestions.length === 0 ? (
                  <p className="speaking-suggestion-empty">发送消息后获取推荐</p>
                ) : (
                  suggestions.map((s, i) => (
                    <button
                      key={i}
                      className="speaking-suggestion"
                      onClick={() => handleSuggestionClick(s)}
                    >
                      <span className="speaking-suggestion-en">{s.en}</span>
                      <span className="speaking-suggestion-zh">{s.zh}</span>
                    </button>
                  ))
                )}
              </div>
            </div>
          </section>
        </div>
      </div>
    </div>
  )
}
