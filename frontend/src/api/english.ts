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

/** 口语对话请求体 */
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

/** 口语对话响应体 */
export interface SpeakingChatResponse {
  ai_reply: string
  translation: string
  suggestions: SpeakingSuggestion[]
  /** 用户上一条消息的中文翻译 */
  user_translation: string
}

// ---------- 接口 ----------

/** 发送口语对话消息，返回 AI 回复、翻译与推荐句子 */
export function sendSpeakingMessage(data: SpeakingChatRequest) {
  return api.post<SpeakingChatResponse>('/english/speaking/chat', data)
}
