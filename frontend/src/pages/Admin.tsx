import { useEffect, useState, type FormEvent } from 'react'
import { banUser, getStats, getUsers, unbanUser } from '../api/admin'
import { getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import Footer from '../components/Footer'
import Navbar from '../components/Navbar'
import type { AdminStats, AdminUser } from '../types'
import './Admin.css'

// 在线判定：5 分钟内活跃
const ONLINE_MS = 5 * 60 * 1000

const DAY_OPTIONS = [
  { days: 1, label: '1天' },
  { days: 7, label: '7天' },
  { days: 30, label: '30天' },
  { days: 0, label: '永久' },
]

function formatDateTime(s: string | null): string {
  if (!s) return '—'
  const d = new Date(s)
  if (Number.isNaN(d.getTime())) return '—'
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())} ${pad(d.getHours())}:${pad(d.getMinutes())}`
}

function isOnline(u: AdminUser): boolean {
  return !!u.last_active_at && Date.now() - new Date(u.last_active_at).getTime() < ONLINE_MS
}

function banUntilLabel(u: AdminUser): string {
  if (!u.banned_until) return '永久封禁'
  if (new Date(u.banned_until).getFullYear() >= 2099) return '永久封禁'
  return `封禁至 ${u.banned_until.slice(0, 10)}`
}

export default function Admin() {
  const { user, logout } = useAuth()
  const [stats, setStats] = useState<AdminStats>({
    total_users: 0,
    online_users: 0,
    banned_users: 0,
  })
  const [users, setUsers] = useState<AdminUser[]>([])
  const [total, setTotal] = useState(0)
  const [page, setPage] = useState(1)
  const pageSize = 20
  const [search, setSearch] = useState('')
  const [searchInput, setSearchInput] = useState('')
  const [statusFilter, setStatusFilter] = useState('all')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [message, setMessage] = useState('')
  const [banTarget, setBanTarget] = useState<AdminUser | null>(null)
  const [banDays, setBanDays] = useState(1)
  const [banning, setBanning] = useState(false)

  const totalPages = Math.max(1, Math.ceil(total / pageSize))

  const loadStats = async () => {
    try {
      const res = await getStats()
      setStats(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const loadUsers = async () => {
    setLoading(true)
    try {
      const res = await getUsers({
        page,
        page_size: pageSize,
        search,
        status_filter: statusFilter,
      })
      setUsers(res.data.users)
      setTotal(res.data.total)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    loadStats()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [])

  useEffect(() => {
    loadUsers()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [page, search, statusFilter])

  const refresh = () => {
    loadStats()
    loadUsers()
  }

  const handleSearch = (e: FormEvent) => {
    e.preventDefault()
    setPage(1)
    setSearch(searchInput.trim())
  }

  const openBan = (u: AdminUser) => {
    setBanTarget(u)
    setBanDays(1)
  }

  const handleConfirmBan = async () => {
    if (!banTarget) return
    setBanning(true)
    setError('')
    setMessage('')
    try {
      await banUser(banTarget.id, banDays)
      setMessage('封禁成功')
      setBanTarget(null)
      refresh()
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setBanning(false)
    }
  }

  const handleUnban = async (u: AdminUser) => {
    setError('')
    setMessage('')
    try {
      await unbanUser(u.id)
      setMessage('解封成功')
      refresh()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="admin-page">
      <Navbar
        active="admin"
        trailing={
          <>
            <span className="navbar-email">{user?.email || user?.username}</span>
            <button className="navbar-btn" onClick={logout}>
              退出登录
            </button>
          </>
        }
      />

      <main className="admin-main">
        <h1 className="admin-title">用户管理</h1>
        <span className="admin-accent" aria-hidden="true" />

        {error && <p className="admin-notice admin-notice-error">{error}</p>}
        {message && <p className="admin-notice admin-notice-ok">{message}</p>}

        <section className="admin-stats">
          <div className="admin-stat-card admin-stat-blue">
            <div className="admin-stat-info">
              <div className="admin-stat-value">{stats.total_users}</div>
              <div className="admin-stat-label">总用户数</div>
            </div>
            <div className="admin-stat-icon">👥</div>
          </div>
          <div className="admin-stat-card admin-stat-green">
            <div className="admin-stat-info">
              <div className="admin-stat-value">{stats.online_users}</div>
              <div className="admin-stat-label">在线用户</div>
            </div>
            <div className="admin-stat-icon">🟢</div>
          </div>
          <div className="admin-stat-card admin-stat-red">
            <div className="admin-stat-info">
              <div className="admin-stat-value">{stats.banned_users}</div>
              <div className="admin-stat-label">封禁用户</div>
            </div>
            <div className="admin-stat-icon">🚫</div>
          </div>
        </section>

        <section className="admin-toolbar">
          <form className="admin-search" onSubmit={handleSearch}>
            <input
              value={searchInput}
              onChange={(e) => setSearchInput(e.target.value)}
              placeholder="按邮箱搜索"
            />
            <button type="submit">搜索</button>
          </form>
          <select
            className="admin-filter"
            value={statusFilter}
            onChange={(e) => {
              setPage(1)
              setStatusFilter(e.target.value)
            }}
          >
            <option value="all">全部</option>
            <option value="active">正常</option>
            <option value="banned">封禁</option>
          </select>
        </section>

        <section className="admin-table-wrap">
          <table className="admin-table">
            <thead>
              <tr>
                <th>ID</th>
                <th>邮箱</th>
                <th>昵称</th>
                <th>角色</th>
                <th>状态</th>
                <th>注册时间</th>
                <th>最后活跃</th>
                <th>操作</th>
              </tr>
            </thead>
            <tbody>
              {loading ? (
                <tr>
                  <td colSpan={8} className="admin-empty">加载中…</td>
                </tr>
              ) : users.length === 0 ? (
                <tr>
                  <td colSpan={8} className="admin-empty">暂无用户</td>
                </tr>
              ) : (
                users.map((u) => (
                  <tr key={u.id}>
                    <td>{u.id}</td>
                    <td className="admin-email">{u.email}</td>
                    <td>{u.username || '—'}</td>
                    <td>
                      {u.role === 'admin' ? (
                        <span className="admin-role admin-role-admin">管理员</span>
                      ) : (
                        <span className="admin-role admin-role-user">用户</span>
                      )}
                    </td>
                    <td>
                      {u.status === 'banned' ? (
                        <span className="admin-status admin-status-banned">
                          <span className="admin-dot admin-dot-red" />
                          {banUntilLabel(u)}
                        </span>
                      ) : isOnline(u) ? (
                        <span className="admin-status admin-status-online">
                          <span className="admin-dot admin-dot-green" />
                          在线
                        </span>
                      ) : (
                        <span className="admin-status admin-status-offline">
                          <span className="admin-dot admin-dot-gray" />
                          离线
                        </span>
                      )}
                    </td>
                    <td>{formatDateTime(u.created_at)}</td>
                    <td>{formatDateTime(u.last_active_at)}</td>
                    <td>
                      {u.status === 'banned' ? (
                        <button
                          className="admin-btn admin-btn-unban"
                          onClick={() => handleUnban(u)}
                        >
                          解封
                        </button>
                      ) : (
                        <button
                          className="admin-btn admin-btn-ban"
                          onClick={() => openBan(u)}
                        >
                          封禁
                        </button>
                      )}
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </section>

        <section className="admin-pagination">
          <button disabled={page <= 1} onClick={() => setPage((p) => p - 1)}>
            上一页
          </button>
          <span>{page} / {totalPages}</span>
          <button disabled={page >= totalPages} onClick={() => setPage((p) => p + 1)}>
            下一页
          </button>
        </section>
      </main>

      {banTarget && (
        <div className="admin-modal-overlay" onClick={() => setBanTarget(null)}>
          <div className="admin-modal" onClick={(e) => e.stopPropagation()}>
            <h3>封禁用户</h3>
            <p className="admin-modal-tip">确定要封禁该用户吗？</p>
            <p className="admin-modal-email">{banTarget.email}</p>
            <div className="admin-modal-days">
              {DAY_OPTIONS.map((opt) => (
                <button
                  key={opt.days}
                  className={banDays === opt.days ? 'admin-day admin-day-active' : 'admin-day'}
                  onClick={() => setBanDays(opt.days)}
                >
                  {opt.label}
                </button>
              ))}
            </div>
            <div className="admin-modal-actions">
              <button className="admin-modal-cancel" onClick={() => setBanTarget(null)}>
                取消
              </button>
              <button
                className="admin-modal-confirm"
                onClick={handleConfirmBan}
                disabled={banning}
              >
                {banning ? '封禁中...' : '确认封禁'}
              </button>
            </div>
          </div>
        </div>
      )}

      <Footer />
    </div>
  )
}
