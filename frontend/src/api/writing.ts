import api from './client'

// ---------- 类型定义 ----------

/** 批改中的一处错误：原句（英文）+ 错误说明（中文）+ 修改建议（英文） */
export interface WritingErrorItem {
  sentence: string
  error: string
  fix: string
}

/** AI 批改结果：三个分项分 + 错误列表 + 建议 + 范文 */
export interface WritingFeedback {
  grammar_score: number
  structure_score: number
  vocab_score: number
  errors: WritingErrorItem[]
  suggestions: string
  sample: string
}

/** 提交 / 详情返回的完整写作结果 */
export interface WritingResult {
  id: number
  topic: string
  category: string
  difficulty: string
  content: string
  score: number | null
  feedback: WritingFeedback
  created_at: string
}

/** 写作历史列表项：题目 + 分数 + 时间 */
export interface WritingHistoryItem {
  id: number
  topic: string
  category: string
  difficulty: string
  score: number | null
  created_at: string
}

/** 提交作文请求体 */
export interface WritingSubmitPayload {
  topic: string
  category: string
  difficulty: string
  content: string
}

// ---------- 接口 ----------

/** 提交作文，返回 AI 完整批改结果 */
export function submitWriting(data: WritingSubmitPayload) {
  return api.post<WritingResult>('/writing/submit', data)
}

/** 获取当前用户的写作历史（按时间倒序） */
export function getWritingHistory() {
  return api.get<WritingHistoryItem[]>('/writing/history')
}

/** 获取单条写作详情（内容 + 批改结果） */
export function getWritingDetail(id: number) {
  return api.get<WritingResult>(`/writing/${id}`)
}

// ---------- 管理员生成题目 ----------

/** 管理员 AI 生成的写作题目 */
export interface WritingTopic {
  id: number
  category: string
  topic: string
  difficulty: string
}

/** 获取某分类下管理员生成的题目 */
export function getWritingTopics(category: string) {
  return api.get<WritingTopic[]>('/writing/topics', { params: { category } })
}

/** 管理员调用 AI 生成题目 */
export function generateTopics(category: string, count: number) {
  return api.post<WritingTopic[]>('/writing/generate-topics', { category, count })
}
