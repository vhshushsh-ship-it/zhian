export interface User {
  id: number
  username: string | null
  email: string
  role: string
  created_at: string
}

export interface AdminUser {
  id: number
  email: string
  username: string | null
  role: string
  status: string
  banned_until: string | null
  last_active_at: string | null
  created_at: string
}

export interface AdminStats {
  total_users: number
  online_users: number
  banned_users: number
}

export interface AdminUserList {
  total: number
  page: number
  page_size: number
  users: AdminUser[]
}
