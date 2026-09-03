import { useNavigate, useParams } from 'react-router-dom'
import { useAuth } from '../auth/AuthContext'
import Navbar from '../components/Navbar'
import './Subject.css'

interface SubjectInfo {
  name: string
  desc: string
}

const SUBJECTS: Record<string, SubjectInfo> = {
  english: { name: '英语', desc: '从单词到听力，全方位提升英语能力' },
  math: { name: '数学', desc: '从基础到进阶，攻克数学重难点' },
  cs: { name: '计算机与网络', desc: '深入理解计算机核心概念与网络原理' },
}

/** 学科占位页：通过 /subject/:id 路由参数复用 */
export default function Subject() {
  const { id } = useParams<{ id: string }>()
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  const info = id ? SUBJECTS[id] : undefined
  const name = info?.name ?? '未知科目'
  const desc = info?.desc ?? ''

  return (
    <div className="subject-page">
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

      <main className="subject-main">
        <h1 className="subject-title">{name}</h1>
        <span className="subject-accent" aria-hidden="true" />
        <p className="subject-desc">{desc}</p>

        <div className="subject-placeholder">
          {/* 建设中图标（CSS 绘制，不用外部图片） */}
          <div className="subject-construction" aria-hidden="true">
            <div className="subject-cone" />
            <span className="subject-cone-stripe" />
            <div className="subject-cone-base" />
          </div>
          <p className="subject-placeholder-title">功能建设中，敬请期待</p>
          <p className="subject-placeholder-sub">
            AI 学习功能正在紧张开发中，稍后再来看看吧
          </p>
        </div>

      </main>

      <button className="subject-back" onClick={() => navigate(-1)}>
        ← 返回
      </button>
    </div>
  )
}
