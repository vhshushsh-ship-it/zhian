import api from './client'

// ---------- 类型定义 ----------

/** 话题：日常对话 / 面试 / 旅游 / 校园 */
export type Topic = 'daily' | 'interview' | 'travel' | 'campus'

/** 难度：初级 / 中级 / 高级 */
export type Level = 'beginner' | 'intermediate' | 'advanced'

/** 对话中的一条消息 */
export interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
}

/** 口语对话请求体（无状态接口） */
export interface SpeakingChatRequest {
  messages: ChatMessage[]
  topic: Topic
  level: Level
}

/** 推荐回复句子 */
export interface SpeakingSuggestion {
  en: string
  zh: string
}

/** 口语对话响应体（无状态接口） */
export interface SpeakingChatResponse {
  ai_reply: string
  translation: string
  suggestions: SpeakingSuggestion[]
  /** 用户上一条消息的中文翻译 */
  user_translation: string
}

// ---------- 有状态类型（对话历史） ----------

/** 对话列表项 */
export interface ConversationSummary {
  id: number
  title: string
  topic: Topic
  level: Level
  updated_at: string
}

/** 对话详情中的一条消息 */
export interface ConversationMessage {
  role: 'user' | 'assistant'
  content: string
  translation: string
  created_at: string
}

/** 对话详情 */
export interface ConversationDetail {
  id: number
  title: string
  topic: Topic
  level: Level
  messages: ConversationMessage[]
}

/** 发送消息响应 */
export interface SendMessageResponse {
  ai_reply: string
  translation: string
  user_translation: string
  suggestions: SpeakingSuggestion[]
}

// ---------- 接口 ----------

/** 发送口语对话消息（无状态，兼容保留） */
export function sendSpeakingMessage(data: SpeakingChatRequest) {
  return api.post<SpeakingChatResponse>('/english/speaking/chat', data)
}

/** 获取当前用户的对话列表（按更新时间倒序） */
export function getConversations() {
  return api.get<ConversationSummary[]>('/english/speaking/conversations')
}

/** 新建对话，返回对话 id */
export function createConversation(topic: Topic, level: Level) {
  return api.post<{ id: number }>('/english/speaking/conversations', { topic, level })
}

/** 获取对话详情（含全部消息） */
export function getConversation(id: number) {
  return api.get<ConversationDetail>(`/english/speaking/conversations/${id}`)
}

/** 向对话发送消息，返回 AI 回复 + 翻译 + 推荐句子 */
export function sendMessage(id: number, content: string) {
  return api.post<SendMessageResponse>(`/english/speaking/conversations/${id}/messages`, {
    content,
  })
}

/** 删除对话 */
export function deleteConversation(id: number) {
  return api.delete(`/english/speaking/conversations/${id}`)
}

// ---------- 语音合成（TTS） ----------

/**
 * 返回某段文本的 TTS 音频流地址，可直接作为 <audio> 的 src。
 * 因为 <audio> 标签无法携带 Authorization 请求头，所以把 JWT 作为
 * token query 参数附加到 URL 上，后端用该参数完成鉴权。
 */
export function getTtsUrl(text: string, rate: number): string {
  const token = localStorage.getItem('token') || ''
  return `/api/tts/speak?text=${encodeURIComponent(text)}&rate=${rate}&token=${encodeURIComponent(token)}`
}
