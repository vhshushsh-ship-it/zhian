/** 高等数学章节与子页的静态配置（后续可换成后端接口） */

export interface Chapter {
  id: string
  label: string
}

export interface SubItem {
  id: string
  label: string
  icon: string
}

export const CHAPTERS: Chapter[] = [
  { id: 'limit', label: '一、极限' },
  { id: 'derivative', label: '二、导数' },
  { id: 'integral', label: '三、不定积分' },
  { id: 'definite-integral', label: '四、定积分' },
  { id: 'differential-equation', label: '五、微分方程' },
  { id: 'multivariable', label: '六、多元函数' },
  { id: 'double-integral', label: '七、二重积分' },
  { id: 'series', label: '八、级数' },
  { id: 'vector-algebra', label: '九、向量代数' },
  { id: 'line-plane', label: '十、直线与平面' },
]

export const SUB_ITEMS: SubItem[] = [
  { id: 'videos', label: '视频讲解', icon: '📺' },
  { id: 'notes', label: '知识点梳理', icon: '📖' },
  { id: 'practice', label: '例题练习', icon: '✏️' },
]

/** 已有真实内容的章节 id，其余章节显示「内容整理中」 */
export const READY_CHAPTER_IDS = new Set(['limit'])
