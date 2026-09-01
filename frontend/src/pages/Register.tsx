import { useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import AuthLayout from '../components/AuthLayout'

export default function Register() {
  const { register } = useAuth()
  const navigate = useNavigate()
  const [username, setUsername] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    // 前端校验：两次密码一致
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setSubmitting(true)
    try {
      // 邮箱为后端可选字段，本次表单未提供，传空字符串（AuthContext 会转为 null）
      await register(username, '', password)
      navigate('/dashboard')
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <AuthLayout
      cardTitle="注册"
      brandTitle="加入知岸"
      brandSubtitle="开启 AI 高效学习新时代"
      switchLink={
        <>
          已有账号？<Link to="/login">去登录</Link>
        </>
      }
    >
      <form className="auth-form" onSubmit={onSubmit}>
        {error && <p className="auth-error">{error}</p>}
        <label htmlFor="username">用户名</label>
        <input
          id="username"
          value={username}
          onChange={(e) => setUsername(e.target.value)}
          autoComplete="username"
          minLength={3}
          required
        />
        <label htmlFor="password">密码</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          minLength={6}
          required
        />
        <label htmlFor="confirm-password">确认密码</label>
        <input
          id="confirm-password"
          type="password"
          value={confirmPassword}
          onChange={(e) => setConfirmPassword(e.target.value)}
          autoComplete="new-password"
          minLength={6}
          required
        />
        <button type="submit" className="auth-submit" disabled={submitting}>
          {submitting ? '注册中...' : '注册'}
        </button>
      </form>
    </AuthLayout>
  )
}
