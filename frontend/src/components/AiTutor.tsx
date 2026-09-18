import { useEffect, useRef, useState, type KeyboardEvent } from 'react'
import { useLocation } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import {
  createAiConversation,
  deleteAiConversation,
  getAiConversation,
  getAiConversations,
  getAiProfile,
  sendAiMessage,
  updateAiProfile,
  type AiPage,
  type AiTutorConversationSummary,
} from '../api/aiTutor'
import './AiTutor.css'

/** 抽屉内的一条消息（system 用于本地提示，不入库） */
interface Message {
  role: 'user' | 'assistant' | 'system'
  content: string
}

/** 从当前路由推导页面标识（场景感知） */
function detectPage(pathname: string): AiPage {
  if (pathname.startsWith('/english/words')) return 'words'
  if (pathname.startsWith('/english/speaking')) return 'speaking'
  if (pathname.startsWith('/english/reading')) return 'reading'
  return 'english'
}

const PAGE_LABELS: Record<AiPage, string> = {
  words: '背单词',
  speaking: '口语练习',
  reading: '外刊精读',
  english: '英语主页',
}

/**
 * 全局悬浮 AI 助手「小岸」。
 * 仅出现在英语模块页面（/english*），右下角悬浮按钮 + 右侧聊天抽屉。
 * 具备场景感知、短期记忆（后端带最近 20 条）、长期画像、数据驱动。
 */
export default function AiTutor() {
  const location = useLocation()
  const pathname = location.pathname

  const [open, setOpen] = useState(false)
  const [conversations, setConversations] = useState<AiTutorConversationSummary[]>([])
  const [currentId, setCurrentId] = useState<number | null>(null)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [sending, setSending] = useState(false)
  const [error, setError] = useState('')

  // 长期画像
  const [profileOpen, setProfileOpen] = useState(false)
  const [goal, setGoal] = useState('')
  const [examDate, setExamDate] = useState('')
  const [weakPoints, setWeakPoints] = useState('')
  const [savingProfile, setSavingProfile] = useState(false)

  const initializedRef = useRef(false)
  const chatListRef = useRef<HTMLDivElement>(null)

  // 自动滚动到最新消息（须在条件返回之前，保证 hooks 顺序稳定）
  useEffect(() => {
    if (chatListRef.current) {
      chatListRef.current.scrollTop = chatListRef.current.scrollHeight
    }
  }, [messages])

  // 仅英语模块页面展示
  if (!pathname.startsWith('/english')) return null
  const page = detectPage(pathname)

  /** 加载长期画像到表单 */
  const loadProfile = async () => {
    try {
      const res = await getAiProfile()
      const p = res.data
      setGoal(p.goal ?? '')
      setExamDate(p.exam_date ?? '')
      setWeakPoints((p.weak_points ?? []).join('、'))
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 初始化：首次展开抽屉时加载画像 + 对话列表 */
  const ensureInit = async () => {
    if (initializedRef.current) return
    initializedRef.current = true
    await loadProfile()
    try {
      const res = await getAiConversations()
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
  }

  /** 加载指定对话详情 */
  const loadConversation = async (id: number) => {
    try {
      const res = await getAiConversation(id)
      const detail = res.data
      setCurrentId(detail.id)
      setMessages(
        detail.messages.map((m) => ({ role: m.role, content: m.content })),
      )
      setError('')
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 新建对话 */
  const handleNewConversation = async () => {
    try {
      const res = await createAiConversation()
      setCurrentId(res.data.id)
      setMessages([])
      setInput('')
      setError('')
      const listRes = await getAiConversations()
      setConversations(listRes.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  /** 删除对话 */
  const handleDeleteConversation = async (id: number) => {
    try {
      await deleteAiConversation(id)
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

  /** 打开抽屉（首次触发初始化） */
  const handleOpen = () => {
    setOpen(true)
    void ensureInit()
  }

  /** 发送消息 */
  const handleSend = async () => {
    const text = input.trim()
    if (!text || sending || currentId == null) return

    setMessages((prev) => [...prev, { role: 'user', content: text }])
    setInput('')
    setSending(true)
    setError('')

    try {
      const res = await sendAiMessage(currentId, text, page)
      setMessages((prev) => [...prev, { role: 'assistant', content: res.data.ai_reply }])
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  /** Enter 发送，Shift+Enter 换行 */
  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSend()
    }
  }

  /** 保存长期画像 */
  const handleSaveProfile = async () => {
    setSavingProfile(true)
    setError('')
    try {
      const weak = weakPoints
        .split(/[、,，\n]/)
        .map((s) => s.trim())
        .filter(Boolean)
      await updateAiProfile({
        goal: goal.trim() || null,
        exam_date: examDate || null,
        weak_points: weak,
      })
      setProfileOpen(false)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSavingProfile(false)
    }
  }

  return (
    <>
      {/* 悬浮按钮 */}
      <button
        className="ai-tutor-fab"
        onClick={handleOpen}
        title="小岸 · AI 导师"
        aria-label="打开 AI 导师"
      >
        <span className="ai-tutor-fab-emoji" aria-hidden="true">🤖</span>
        <span className="ai-tutor-fab-text">小岸</span>
      </button>

      {/* 右侧聊天抽屉 */}
      {open && (
        <div className="ai-tutor-drawer">
          <header className="ai-tutor-header">
            <div className="ai-tutor-header-title">
              <span className="ai-tutor-header-emoji" aria-hidden="true">🤖</span>
              <div>
                <p className="ai-tutor-header-name">小岸 · AI 导师</p>
                <p className="ai-tutor-header-page">当前：{PAGE_LABELS[page]}</p>
              </div>
            </div>
            <div className="ai-tutor-header-actions">
              <button
                className="ai-tutor-icon-btn"
                onClick={() => setProfileOpen((v) => !v)}
                title="学习目标"
                aria-label="学习目标"
              >
                🎯
              </button>
              <button
                className="ai-tutor-icon-btn"
                onClick={handleNewConversation}
                title="新对话"
                aria-label="新对话"
              >
                ＋
              </button>
              <button
                className="ai-tutor-icon-btn"
                onClick={() => setOpen(false)}
                title="关闭"
                aria-label="关闭"
              >
                ✕
              </button>
            </div>
          </header>

          {/* 长期画像编辑 */}
          {profileOpen && (
            <section className="ai-tutor-profile">
              <label className="ai-tutor-profile-label">
                学习目标
                <input
                  value={goal}
                  onChange={(e) => setGoal(e.target.value)}
                  placeholder="如：考研英语 70 分"
                />
              </label>
              <label className="ai-tutor-profile-label">
                考试日期
                <input
                  type="date"
                  value={examDate}
                  onChange={(e) => setExamDate(e.target.value)}
                />
              </label>
              <label className="ai-tutor-profile-label">
                薄弱项（用顿号/逗号分隔）
                <input
                  value={weakPoints}
                  onChange={(e) => setWeakPoints(e.target.value)}
                  placeholder="如：长难句、听力、写作"
                />
              </label>
              <button
                className="ai-tutor-profile-save"
                onClick={handleSaveProfile}
                disabled={savingProfile}
              >
                {savingProfile ? '保存中...' : '保存画像'}
              </button>
            </section>
          )}

          {/* 历史对话 */}
          {conversations.length > 0 && (
            <div className="ai-tutor-history">
              {conversations.map((c) => (
                <div
                  key={c.id}
                  className={
                    c.id === currentId
                      ? 'ai-tutor-history-item ai-tutor-history-item-active'
                      : 'ai-tutor-history-item'
                  }
                  onClick={() => loadConversation(c.id)}
                >
                  <span className="ai-tutor-history-title">{c.title}</span>
                  <button
                    className="ai-tutor-history-delete"
                    onClick={(e) => {
                      e.stopPropagation()
                      handleDeleteConversation(c.id)
                    }}
                  >
                    删除
                  </button>
                </div>
              ))}
            </div>
          )}

          {/* 消息列表 */}
          <div className="ai-tutor-chat-list" ref={chatListRef}>
            {messages.length === 0 ? (
              <div className="ai-tutor-empty">
                <p className="ai-tutor-empty-emoji" aria-hidden="true">👋</p>
                <p>你好，我是小岸！</p>
                <p className="ai-tutor-empty-sub">
                  问我背单词、口语、阅读的问题吧，我会结合你的学习情况给建议。
                </p>
              </div>
            ) : (
              messages.map((m, i) => (
                <div key={i} className={`ai-tutor-msg ai-tutor-msg-${m.role}`}>
                  <div className="ai-tutor-bubble">{m.content}</div>
                </div>
              ))
            )}
            {sending && (
              <div className="ai-tutor-msg ai-tutor-msg-assistant">
                <div className="ai-tutor-bubble ai-tutor-bubble-typing">思考中…</div>
              </div>
            )}
          </div>

          {/* 输入区 */}
          <div className="ai-tutor-input">
            {error && <p className="ai-tutor-error">{error}</p>}
            <textarea
              className="ai-tutor-textarea"
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="输入你的问题，Enter 发送，Shift+Enter 换行"
            />
            <button
              className="ai-tutor-send"
              onClick={handleSend}
              disabled={sending || currentId == null}
            >
              {sending ? '发送中…' : '发送'}
            </button>
          </div>
        </div>
      )}
    </>
  )
}
