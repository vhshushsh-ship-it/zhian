import axios from 'axios'

const api = axios.create({
  baseURL: '/api',
})

// 请求拦截器：自动附加 JWT
api.interceptors.request.use((config) => {
  const token = localStorage.getItem('token')
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

// 响应拦截器：统一处理认证与封禁错误
api.interceptors.response.use(
  (res) => res,
  (error) => {
    // 401：未登录或 token 过期
    if (error.response?.status === 401) {
      localStorage.removeItem('token')
      const path = window.location.pathname
      if (!path.startsWith('/login') && !path.startsWith('/register')) {
        window.location.href = '/login'
      }
    }

    // 403：封禁或权限不足
    if (error.response?.status === 403) {
      const msg = error.response?.data?.detail || ''
      // 只要是封禁相关的错误，强制退出
      if (msg.includes('封禁') || msg.includes('banned')) {
        localStorage.removeItem('token')
        window.location.href = '/login?banned=' + encodeURIComponent(msg)
      }
    }

    return Promise.reject(error)
  },
)

// 从 axios 错误中提取后端返回的 detail 信息
export function getErrorMessage(err: unknown): string {
  if (axios.isAxiosError(err)) {
    const data = err.response?.data as { detail?: string } | undefined
    if (data?.detail) return data.detail
    return err.message
  }
  return '请求失败，请稍后重试'
}

export default api
