import api from './client'

// ---------- 类型定义 ----------

/** 一道阅读理解题 */
export interface ReadingQuizItem {
  question: string
  options: string[]
  answer: number
  explanation: string
}

/** 长难句（新文章含预生成翻译与结构分析；旧文章可能仍是字符串） */
export interface ReadingLongSentence {
  sentence: string
  translation: string
  analysis: string
}

/** 文章列表项（不含正文，含当前用户是否已读） */
export interface ReadingArticleListItem {
  id: number
  title: string
  difficulty: string
  topic: string
  word_count: number
  created_at: string
  is_read: boolean
}

/** 文章列表分页响应 */
export interface ReadingArticleListResponse {
  total: number
  page: number
  size: number
  items: ReadingArticleListItem[]
}

/** 当前用户的阅读记录 */
export interface ReadingHistory {
  read_at: string
  quiz_score: number | null
  words_collected: number
}

/** 文章详情（正文 / 长难句 / 题目）+ 当前用户阅读记录 */
export interface ReadingArticleDetail {
  id: number
  title: string
  content: string
  difficulty: string
  topic: string
  word_count: number
  long_sentences: (string | ReadingLongSentence)[]
  quiz: ReadingQuizItem[]
  created_at: string
  history: ReadingHistory | null
}

/** 单题判分结果 */
export interface QuizResultItem {
  question: string
  your_answer: number | null
  correct_answer: number
  is_correct: boolean
  explanation: string
}

/** 做题判分响应 */
export interface QuizSubmitResponse {
  score: number
  correct: number
  total: number
  results: QuizResultItem[]
}

/** 选中即译响应 */
export interface ExplainResponse {
  translation: string
  analysis: string
}

/** 批量生成结果中的一篇文章（精简信息） */
export interface GeneratedArticleItem {
  id: number
  title: string
  difficulty: string
  topic: string
  word_count: number
}

/** 批量生成文章响应 */
export interface GenerateArticleResponse {
  generated: GeneratedArticleItem[]
  total: number
  success: number
  failed: number
}

/** 文章列表查询参数 */
export interface ArticleListParams {
  difficulty?: string
  topic?: string
  page?: number
  size?: number
}

// ---------- 接口 ----------

/** 管理员 AI 生成文章（count 为一次生成数量） */
export function generateArticle(difficulty: string, topic: string, count = 1) {
  return api.post<GenerateArticleResponse>('/reading/generate', { difficulty, topic, count })
}

/** 文章列表（支持难度 / 话题筛选 + 分页） */
export function getArticles(params: ArticleListParams = {}) {
  return api.get<ReadingArticleListResponse>('/reading/articles', { params })
}

/** 文章详情 */
export function getArticle(id: number) {
  return api.get<ReadingArticleDetail>(`/reading/articles/${id}`)
}

/** 标记已读 */
export function markRead(id: number) {
  return api.post<ReadingHistory>(`/reading/articles/${id}/read`)
}

/** 提交做题答案 */
export function submitQuiz(id: number, answers: number[]) {
  return api.post<QuizSubmitResponse>(`/reading/articles/${id}/quiz`, { answers })
}

/** 收集生词 */
export function collectWord(id: number, word: string) {
  return api.post<{ message: string; word: string }>(
    `/reading/articles/${id}/collect-word`,
    { word },
  )
}

/** 选中即译 */
export function explainText(text: string, context: string) {
  return api.post<ExplainResponse>('/reading/explain', { text, context })
}
