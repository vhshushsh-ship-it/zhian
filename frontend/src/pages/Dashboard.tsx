import { useNavigate } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Footer from '../components/Footer'
import Navbar from '../components/Navbar'
import './Dashboard.css'

interface SubjectItem {
  id: string
  name: string
  desc: string
  theme: 'english' | 'math' | 'cs'
  icon: string
}

const SUBJECTS: SubjectItem[] = [
  {
    id: 'english',
    name: '英语',
    desc: '单词、语法、阅读、听力，AI 助你全面提升',
    theme: 'english',
    icon: '📖',
  },
  {
    id: 'math',
    name: '数学',
    desc: '高数、线代、概率，AI 帮你理清思路',
    theme: 'math',
    icon: '📐',
  },
  {
    id: 'cs',
    name: '计算机与网络',
    desc: '数据结构、操作系统、计算机网络，AI 伴你攻克',
    theme: 'cs',
    icon: '💻',
  },
]

/** 登录后的首页：学科选择 */
export default function Dashboard() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="dashboard">
      <Navbar
        active="home"
        trailing={
          <>
            <span className="navbar-email">{user?.email || user?.username}</span>
            <button
              className="navbar-btn"
              onClick={() => {
                logout()
                navigate('/')
              }}
            >
              退出登录
            </button>
          </>
        }
      />

      <main className="dashboard-main">
        <h1 className="dashboard-title">选择学习科目</h1>
        <span className="dashboard-accent" aria-hidden="true" />
        <p className="dashboard-subtitle">AI 加持，让每一次学习都更加高效</p>

        <div className="dashboard-grid">
          {SUBJECTS.map((s) => (
            <div key={s.id} className={`subject-card subject-card-${s.theme}`}>
              <div className={`subject-card-bar subject-card-bar-${s.theme}`} />
              <div className={`subject-icon subject-icon-${s.theme}`}>{s.icon}</div>
              <h2 className="subject-name">{s.name}</h2>
              <p className="subject-desc">{s.desc}</p>
              <button
                className="subject-btn"
                onClick={() => navigate(`/subject/${s.id}`)}
              >
                进入学习
              </button>
            </div>
          ))}
        </div>
      </main>

      <Footer />
    </div>
  )
}
