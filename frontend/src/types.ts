export interface User {
  id: number
  username: string
  email: string | null
  created_at: string
}

export interface Note {
  id: number
  title: string
  content: string
  created_at: string
  updated_at: string
}
