import { useState, type FormEvent } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import AuthLayout from '../components/AuthLayout'

export default function Login() {
  const { login } = useAuth()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [searchParams] = useSearchParams()
  const bannedMsg = searchParams.get('banned')

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    setSubmitting(true)
    try {
      // 登录成功后的跳转由 AuthContext.login 按角色处理
      await login(email, password)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      cardTitle="登录"
      brandTitle="欢迎回来"
      brandSubtitle="继续你的学习之旅"
      switchLink={
        <>
          还没有账号？<Link to="/register">注册</Link>
        </>
      }
    >
      <form className="auth-form" onSubmit={onSubmit}>
        {bannedMsg && <p className="auth-error">{bannedMsg}</p>}
        {error && <p className="auth-error">{error}</p>}
        <label htmlFor="email">邮箱</label>
        <input
          id="email"
          type="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          placeholder="请输入邮箱"
          autoComplete="email"
          required
        />
        <label htmlFor="password">密码</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="current-password"
          required
        />
        <button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? '登录中...' : '登录'}
        </button>
      </form>
    </AuthLayout>
  )
}
