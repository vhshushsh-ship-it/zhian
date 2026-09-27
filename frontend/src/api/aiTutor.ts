import api from './client'

// ---------- 类型定义 ----------

/** 场景感知：当前页面标识 */
export type AiPage = 'words' | 'speaking' | 'reading' | 'english'

/** 用户 AI 导师长期画像 */
export interface AiProfile {
  goal: string | null
  exam_date: string | null
  weak_points: string[]
  learning_style: string | null
  preferences: Record<string, unknown>
  ai_notes: string | null
}

/** 更新画像请求体 */
export interface UpdateAiProfilePayload {
  goal?: string | null
  exam_date?: string | null
  weak_points?: string[]
  learning_style?: string | null
  preferences?: Record<string, unknown>
}

/** 对话列表项 */
export interface AiTutorConversationSummary {
  id: number
  title: string
  created_at: string
}

/** 对话详情中的一条消息 */
export interface AiTutorMessage {
  role: 'user' | 'assistant'
  content: string
  created_at: string
}

/** 对话详情 */
export interface AiTutorConversationDetail {
  id: number
  title: string
  created_at: string
  messages: AiTutorMessage[]
}

// ---------- 接口 ----------

/** 获取用户 AI 导师长期画像 */
export function getAiProfile() {
  return api.get<AiProfile>('/ai-tutor/profile')
}

/** 更新用户 AI 导师长期画像 */
export function updateAiProfile(data: UpdateAiProfilePayload) {
  return api.put<AiProfile>('/ai-tutor/profile', data)
}

/** 获取 AI 导师对话列表（按创建时间倒序） */
export function getAiConversations() {
  return api.get<AiTutorConversationSummary[]>('/ai-tutor/conversations')
}

/** 新建 AI 导师对话，返回对话 id */
export function createAiConversation() {
  return api.post<{ id: number }>('/ai-tutor/conversations')
}

/** 获取对话详情（含全部消息） */
export function getAiConversation(id: number) {
  return api.get<AiTutorConversationDetail>(`/ai-tutor/conversations/${id}`)
}

/** 发送消息：content 用户文本，page 当前页面标识 */
export function sendAiMessage(id: number, content: string, page: AiPage) {
  return api.post<{ ai_reply: string }>(`/ai-tutor/conversations/${id}/messages`, {
    content,
    page,
  })
}

/** 删除对话 */
export function deleteAiConversation(id: number) {
  return api.delete(`/ai-tutor/conversations/${id}`)
}

// ---------- 学习日历 / 每日任务 ----------

/** 单条每日任务 */
export interface DailyTaskItem {
  type: string
  title: string
  done: boolean
}

/** 某天的任务列表 */
export interface WeekDayTasks {
  date: string
  tasks: DailyTaskItem[]
}

/** 未来 7 天任务 */
export interface DailyTasksResponse {
  today: DailyTaskItem[]
  week: WeekDayTasks[]
}

/** 获取未来 7 天的学习任务（今日任务 + 本周计划） */
export function getDailyTasks() {
  return api.get<DailyTasksResponse>('/ai-tutor/daily-tasks')
}

/** AI 重新生成未来 7 天任务，返回最新计划 */
export function refreshPlan() {
  return api.post<DailyTasksResponse>('/ai-tutor/refresh-plan')
}

/** 标记任务完成 / 取消完成 */
export function checkTask(date: string, taskType: string, done: boolean) {
  return api.post('/ai-tutor/daily-tasks/check', { date, task_type: taskType, done })
}
