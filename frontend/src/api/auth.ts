import api from './client'
import type { User } from '../types'

export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

/** 发送邮箱验证码 */
export function sendCode(email: string) {
  return api.post<{ message: string }>('/auth/send-code', { email })
}

/** 邮箱 + 密码登录 */
export function login(email: string, password: string) {
  return api.post<LoginResponse>('/auth/login', { email, password })
}

/** 邮箱验证码注册 */
export function register(
  email: string,
  code: string,
  password: string,
  confirmPassword: string,
) {
  return api.post<LoginResponse>('/auth/register', {
    email,
    code,
    password,
    confirm_password: confirmPassword,
  })
}
