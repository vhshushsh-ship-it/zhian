import api from './client'

// ---------- 类型定义 ----------

/** 概览区核心指标 */
export interface OverviewStats {
  streak_days: number
  total_words_learned: number
  total_words_mastered: number
  words_today_due: number
  recognition_rate: number
  speaking_sessions: number
  speaking_total_messages: number
  last_speaking_at: string | null
  weekly_completion_rate: number
  reading_articles_read: number
}

/** 薄弱词 */
export interface WeakWord {
  word: string
  forgotten_count: number
  memory_strength: number
}

/** 单词学习详情 */
export interface WordsStats {
  current_book: string
  daily_goal: number
  weak_words: WeakWord[]
}

/** 常练话题统计项 */
export interface TopicStat {
  topic: string
  count: number
}

/** 口语练习详情 */
export interface SpeakingStats {
  topics: TopicStat[]
}

/** 近 7 天某天的学习量 */
export interface DailyTrend {
  date: string
  words_reviewed: number
  words_new: number
  speaking_messages: number
}

/** 英语模块聚合学习数据 */
export interface EnglishStats {
  overview: OverviewStats
  words: WordsStats
  speaking: SpeakingStats
  weekly_trend: DailyTrend[]
}

// ---------- 接口 ----------

/** 获取英语模块聚合学习数据 */
export function getEnglishStats() {
  return api.get<EnglishStats>('/english/stats')
}
