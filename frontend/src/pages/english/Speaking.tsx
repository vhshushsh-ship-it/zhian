import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useAuth } from '../../auth/AuthContext'
import Navbar from '../../components/Navbar'
import { getErrorMessage } from '../../api/client'
import {
  sendSpeakingMessage,
  type ChatMessage,
  type Level,
  type SpeakingSuggestion,
  type Topic,
} from '../../api/english'
import './Speaking.css'

/** 页面内的一条消息（system 用于系统提示，不带翻译） */
interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
  translation?: string
}

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

/** 英语口语练习：AI 对话 + 翻译 + 辅助功能 三栏布局 */
export default function Speaking() {
  const { user, logout } = useAuth()

  const [messages, setMessages] = useState<Message[]>([
    {
      role: 'system',
      content: '欢迎来到口语练习！当前话题：日常对话，难度：初级。用英语输入开始对话吧。',
    },
  ])
  const [topic, setTopic] = useState<Topic>('daily')
  const [level, setLevel] = useState<Level>('beginner')
  const [input, setInput] = useState('')
  const [suggestions, setSuggestions] = useState<SpeakingSuggestion[]>([])
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  // 用于自动滚动到最新消息
  const chatListRef = useRef<HTMLDivElement>(null)
  const translationListRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight
    }
    if (translationListRef.current) {
      translationListRef.current.scrollTop = translationListRef.current.scrollHeight
    }
  }, [messages])

  /** 发送消息 */
  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending) return

    const userMsg: Message = { role: 'user', content: text, translation: '' }
    const nextMessages = [...messages, userMsg]

    setMessages(nextMessages)
    setInput('')
    setSending(true)
    setError('')

    try {
      // 只把 user / assistant 消息传给后端
      const apiMessages: ChatMessage[] = nextMessages
        .filter((m): m is Message & { role: 'user' | 'assistant' } => m.role !== 'system')
        .map((m) => ({ role: m.role, content: m.content }))

      const res = await sendSpeakingMessage({
        messages: apiMessages,
        topic,
        level,
      })
      const { ai_reply, translation, user_translation, suggestions: next } = res.data

      // 回填用户消息的中文翻译，并追加 AI 回复
      const updated = nextMessages.map((m) =>
        m === userMsg ? { ...m, translation: user_translation } : m,
      )
      updated.push({ role: 'assistant', content: ai_reply, translation })
      setMessages(updated)
      setSuggestions(next)
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

  /** 切换话题：清空对话，重新开始 */
  const handleTopicChange = (t: Topic) => {
    if (t === topic) return
    setTopic(t)
    setMessages([{ role: 'system', content: `已切换到 ${topicLabel(t)} 话题` }])
    setSuggestions([])
    setInput('')
    setError('')
  }

  /** 切换难度：不清空对话 */
  const handleLevelChange = (l: Level) => {
    setLevel(l)
  }

  /** 点击推荐句子，填入输入框 */
  const handleSuggestionClick = (s: SpeakingSuggestion) => {
    setInput(s.en)
  }

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

            <div className="speaking-chat-list" ref={chatListRef}>
              {messages.map((m, i) => (
                <div key={i} className={`speaking-msg speaking-msg-${m.role}`}>
                  {m.role !== 'system' && (
                    <span className="speaking-msg-role">
                      {m.role === 'user' ? '你' : 'AI'}
                    </span>
                  )}
                  <div className="speaking-bubble">{m.content}</div>
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
                disabled={sending}
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
