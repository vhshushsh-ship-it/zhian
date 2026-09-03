import api from './client'
import type { AdminStats, AdminUserList } from '../types'

export interface AdminUserQuery {
  page: number
  page_size: number
  search?: string
  status_filter?: string
}

/** 获取统计数据 */
export function getStats() {
  return api.get<AdminStats>('/admin/stats')
}

/** 分页获取用户列表 */
export function getUsers(params: AdminUserQuery) {
  return api.get<AdminUserList>('/admin/users', { params })
}

/** 封禁用户（days 为封禁天数，0 表示永久） */
export function banUser(userId: number, days: number) {
  return api.post<{ message: string }>(`/admin/users/${userId}/ban`, { days })
}

/** 解封用户 */
export function unbanUser(userId: number) {
  return api.post<{ message: string }>(`/admin/users/${userId}/unban`)
}
