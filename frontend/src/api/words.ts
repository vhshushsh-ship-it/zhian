import api from './client'

// ---------- 类型定义 ----------

/** 复习反馈：认识 / 模糊 / 忘记 */
export type Feedback = 'known' | 'vague' | 'forgotten'

/** 今日复习队列中的一项 */
export interface TodayQueueItem {
  id: number
  word: string
  phonetic: string | null
  audio_url: string | null
  current_strength: number
  is_new: boolean
  index: number
}

/** 今日复习队列 */
export interface TodayQueueResponse {
  total: number
  review_count: number
  new_count: number
  items: TodayQueueItem[]
}

/** 单词释义 */
export interface WordDefinition {
  pos: string | null
  meaning: string
}

/** 单词例句 */
export interface WordExample {
  en: string
  zh: string | null
}

/** 单词详情 + 当前用户学习进度 */
export interface WordDetail {
  id: number
  word: string
  phonetic: string | null
  audio_url: string | null
  definitions: WordDefinition[]
  examples: WordExample[]
  current_strength: number
  memory_strength: number
  review_count: number
  known_count: number
  vague_count: number
  forgotten_count: number
  is_mastered: boolean
}

/** 复习反馈响应 */
export interface ReviewResponse {
  new_strength: number
  next_review_date: string
  interval_text: string
}

/** 背单词学习统计 */
export interface WordStats {
  learned: number
  due_today: number
  learned_today: number
  mastered: number
  known_count: number
  vague_count: number
  forgotten_count: number
  accuracy: number
  streak_days: number
}

// ---------- 接口 ----------

/** 获取今日复习队列（到期词 + 新词） */
export function getTodayQueue() {
  return api.get<TodayQueueResponse>('/words/today-queue')
}

/** 获取单词详情（释义、例句）+ 当前用户进度 */
export function getWordDetail(id: number) {
  return api.get<WordDetail>(`/words/${id}`)
}

/** 提交复习反馈，返回新记忆强度与下次复习间隔 */
export function submitReview(id: number, feedback: Feedback) {
  return api.post<ReviewResponse>(`/words/${id}/review`, { feedback })
}

/** 获取背单词学习统计 */
export function getStats() {
  return api.get<WordStats>('/words/stats')
}
