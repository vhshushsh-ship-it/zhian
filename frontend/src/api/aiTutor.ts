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

/** 获取唯一对话（不存在则自动创建），含全部消息 */
export function getChatConversation() {
  return api.get<AiTutorConversationDetail>('/ai-tutor/chat')
}

/** 发送消息（单对话，后端自动创建 + 超长自动压缩） */
export function sendChatMessage(content: string, page: AiPage) {
  return api.post<{ ai_reply: string }>('/ai-tutor/chat', { content, page })
}

/** 清空当前用户对话的所有消息 */
export function clearConversation() {
  return api.post('/ai-tutor/clear')
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
