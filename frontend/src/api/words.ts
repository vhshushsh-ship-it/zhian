import api from './client'

// ---------- 类型定义 ----------

/** 复习反馈：认识 / 不确定 / 不认识 */
export type Feedback = 'known' | 'vague' | 'forgotten'

/** 词书 key：考研 / 四级 / 六级 */
export type BookKey = 'kaoyan' | 'cet4' | 'cet6'

/** 单个反馈档位的间隔预览文案 */
export interface IntervalPreview {
  text: string
}

/** 三档反馈的间隔预览 */
export interface TodayQueuePreviews {
  known: IntervalPreview
  vague: IntervalPreview
  forgotten: IntervalPreview
}

/** 今日复习队列中的一项 */
export interface TodayQueueItem {
  id: number
  word: string
  phonetic: string | null
  audio_url: string | null
  current_strength: number
  is_new: boolean
  index: number
  previews: TodayQueuePreviews
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

/** 单本词书的统计信息 */
export interface BookItem {
  key: BookKey
  label: string
  total: number
  learned: number
  mastered: number
  familiar: number
  medium: number
  weak: number
  unlearned: number
}

/** 用户背单词设置 */
export interface WordSettings {
  current_book: BookKey
  daily_new_goal: number
}

// ---------- 接口 ----------

/** 获取今日复习队列（当前词书下到期词 + 新词） */
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

/** 获取三本词书的统计信息 */
export function getBooks() {
  return api.get<BookItem[]>('/words/books')
}

/** 获取用户背单词设置 */
export function getSettings() {
  return api.get<WordSettings>('/words/settings')
}

/** 切换当前学习词书 */
export function selectBook(book: BookKey) {
  return api.post<WordSettings>('/words/select-book', { book })
}

/** 更新每日新词量 */
export function updateSettings(daily_new_goal: number) {
  return api.put<WordSettings>('/words/settings', { daily_new_goal })
}
