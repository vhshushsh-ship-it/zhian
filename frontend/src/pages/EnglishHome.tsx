import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Navbar from '../components/Navbar'
import './EnglishHome.css'

type FeatureId = 'words' | 'speaking' | 'reading'

interface Feature {
  id: FeatureId
  /** 左侧菜单显示名 */
  label: string
  icon: string
  /** 右侧详情标题 */
  title: string
  intro: string
  methods: string[]
  instructions: string[]
  buttonText: string
  path: string
}

const FEATURES: Feature[] = [
  {
    id: 'words',
    label: '单词',
    icon: '📖',
    title: '单词',
    intro: '智能背单词，艾宾浩斯复习，轻松扩充词汇量',
    methods: [
      '采用艾宾浩斯遗忘曲线，科学安排复习时间',
      '每天学习新单词 + 复习旧单词，循序渐进',
      '标记生词、熟词，智能调整学习节奏',
      '配合例句和发音，加深记忆',
    ],
    instructions: [
      '点击「开始学习」进入单词学习页面',
      '选择词库（CET4/CET6/考研等）和每日学习量',
      '认识的单词点「认识」，不认识的点「不认识」',
      '系统自动安排复习，坚持打卡效果更佳',
    ],
    buttonText: '开始背单词',
    path: '/english/words',
  },
  {
    id: 'speaking',
    label: '口语练习',
    icon: '🎤',
    title: '口语练习',
    intro: 'AI 对话练习，实时发音评分，大胆开口说英语',
    methods: [
      '与 AI 进行真实场景对话，模拟日常交流',
      '跟读练习，系统实时评分发音准确度',
      '从简单问候到复杂话题，逐步提升难度',
      '记录常用表达，建立自己的口语语料库',
    ],
    instructions: [
      '点击「开始练习」进入口语练习页面',
      '选择练习模式：AI 对话 / 跟读模仿 / 话题讨论',
      '允许麦克风权限，大声说出来',
      '查看评分和发音建议，反复练习改进',
    ],
    buttonText: '开始口语练习',
    path: '/english/speaking',
  },
  {
    id: 'reading',
    label: '阅读练习',
    icon: '📚',
    title: '阅读练习',
    intro: '精选文章阅读，长难句解析，提升阅读理解能力',
    methods: [
      '精选不同难度的英文文章，循序渐进',
      '遇到生词点击即可查看释义，自动加入生词本',
      '长难句一键解析，理清句子结构',
      '读完文章做阅读理解题，检验学习效果',
    ],
    instructions: [
      '点击「开始阅读」进入阅读练习页面',
      '选择文章难度和主题（科技/文化/经济等）',
      '阅读过程中点击生词查看释义',
      '完成阅读后做配套题目，查看解析',
    ],
    buttonText: '开始阅读',
    path: '/english/reading',
  },
]

/** 学习数据：先写死为 0，后续接入真实数据 */
const LEARNING_DATA = [
  { icon: '📚', label: '已学单词', value: '0 个' },
  { icon: '⏱️', label: '今日学习', value: '0 分钟' },
  { icon: '🔥', label: '连续天数', value: '0 天' },
  { icon: '✅', label: '完成率', value: '0%' },
]

/** 英语首页：左侧功能导航 + 右侧功能介绍 */
export default function EnglishHome() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()
  const [activeId, setActiveId] = useState<FeatureId>('words')

  const active = FEATURES.find((f) => f.id === activeId) ?? FEATURES[0]

  return (
    <div className="english-page">
      <Navbar
        active="home"
        trailing={
          <>
            <span className="navbar-email">{user?.email || user?.username}</span>
            <button className="navbar-btn" onClick={logout}>
              退出登录
            </button>
          </>
        }
      />

      <div className="english-layout">
        {/* 左侧导航 */}
        <aside className="english-sidebar">
          <div className="english-sidebar-title">
            <h1>英语</h1>
            <p>English Learning</p>
            <span className="english-sidebar-accent" aria-hidden="true" />
          </div>

          <nav className="english-menu">
            {FEATURES.map((f) => (
              <button
                key={f.id}
                className={
                  f.id === activeId
                    ? 'english-menu-item english-menu-item-active'
                    : 'english-menu-item'
                }
                onClick={() => setActiveId(f.id)}
              >
                <span className="english-menu-icon">{f.icon}</span>
                <span>{f.label}</span>
              </button>
            ))}
          </nav>

          <div className="english-data">
            <h3>学习数据</h3>
            {LEARNING_DATA.map((d) => (
              <div key={d.label} className="english-data-item">
                <span className="english-data-icon">{d.icon}</span>
                <span className="english-data-label">{d.label}</span>
                <span className="english-data-value">{d.value}</span>
              </div>
            ))}
          </div>
        </aside>

        {/* 右侧内容 */}
        <main className="english-content">
          <h2 className="english-content-title">{active.title}</h2>
          <span className="english-content-accent" aria-hidden="true" />
          <p className="english-content-intro">{active.intro}</p>

          <div className="english-detail-card">
            <section className="english-detail-section">
              <h3 className="english-detail-heading">学习方法</h3>
              <ul className="english-detail-list">
                {active.methods.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </section>

            <section className="english-detail-section">
              <h3 className="english-detail-heading">使用说明</h3>
              <ul className="english-detail-list">
                {active.instructions.map((m) => (
                  <li key={m}>{m}</li>
                ))}
              </ul>
            </section>
          </div>

          <button
            className="english-start-btn"
            onClick={() => navigate(active.path)}
          >
            {active.buttonText}
          </button>
        </main>
      </div>

      <button className="english-back" onClick={() => navigate(-1)}>
        ← 返回
      </button>
    </div>
  )
}
