import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { sendCode } from '../api/auth'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import AuthLayout from '../components/AuthLayout'
import './Register.css'

const EMAIL_RE = /^[^\s@]+@[^\s@]+\.[^\s@]+$/

export default function Register() {
  const { register } = useAuth()
  const [email, setEmail] = useState('')
  const [code, setCode] = useState('')
  const [password, setPassword] = useState('')
  const [confirmPassword, setConfirmPassword] = useState('')
  const [error, setError] = useState('')
  const [submitting, setSubmitting] = useState(false)
  const [sending, setSending] = useState(false)
  const [countdown, setCountdown] = useState(0)

  // 验证码倒计时
  useEffect(() => {
    if (countdown <= 0) return
    const timer = setTimeout(() => setCountdown((c) => c - 1), 1000)
    return () => clearTimeout(timer)
  }, [countdown])

  const handleSendCode = async () => {
    if (!EMAIL_RE.test(email)) {
      setError('请输入正确的邮箱地址')
      return
    }
    setError('')
    setSending(true)
    try {
      await sendCode(email)
      setCountdown(60)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setSending(false)
    }
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')

    if (!EMAIL_RE.test(email)) {
      setError('请输入正确的邮箱地址')
      return
    }
    if (code.length !== 6) {
      setError('请输入 6 位验证码')
      return
    }
    if (password.length < 6) {
      setError('密码长度至少 6 位')
      return
    }
    if (password !== confirmPassword) {
      setError('两次输入的密码不一致')
      return
    }

    setSubmitting(true)
    try {
      // 注册成功后的跳转由 AuthContext.register 处理（普通用户 → /dashboard）
      await register(email, code, password, confirmPassword)
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

        <label htmlFor="code">验证码</label>
        <div className="auth-code-row">
          <input
            id="code"
            className="auth-code-input"
            value={code}
            onChange={(e) => setCode(e.target.value.replace(/\D/g, ''))}
            placeholder="请输入验证码"
            inputMode="numeric"
            maxLength={6}
            required
          />
          <button
            type="button"
            className="auth-code-btn"
            onClick={handleSendCode}
            disabled={sending || countdown > 0}
          >
            {sending ? '发送中...' : countdown > 0 ? `${countdown}s 后重发` : '获取验证码'}
          </button>
        </div>

        <label htmlFor="password">密码</label>
        <input
          id="password"
          type="password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          placeholder="请输入密码（至少6位）"
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
          placeholder="请确认密码"
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
