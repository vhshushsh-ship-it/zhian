import { useEffect, useState, type FormEvent } from 'react'
import api, { getErrorMessage } from '../api/client'
import { useAuth } from '../auth/AuthContext'
import type { Note } from '../types'

export default function Notes() {
  const { user, logout } = useAuth()
  const [notes, setNotes] = useState<Note[]>([])
  const [title, setTitle] = useState('')
  const [content, setContent] = useState('')
  const [editing, setEditing] = useState<Note | null>(null)
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)

  const fetchNotes = async () => {
    try {
      const res = await api.get<Note[]>('/notes')
      setNotes(res.data)
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchNotes()
  }, [])

  const resetForm = () => {
    setTitle('')
    setContent('')
    setEditing(null)
  }

  const onSubmit = async (e: FormEvent) => {
    e.preventDefault()
    setError('')
    try {
      if (editing) {
        await api.put(`/notes/${editing.id}`, { title, content })
      } else {
        await api.post('/notes', { title, content })
      }
      resetForm()
      fetchNotes()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  const startEdit = (note: Note) => {
    setEditing(note)
    setTitle(note.title)
    setContent(note.content)
  }

  const remove = async (id: number) => {
    if (!window.confirm('确定删除这条笔记吗？')) return
    try {
      await api.delete(`/notes/${id}`)
      fetchNotes()
    } catch (err) {
      setError(getErrorMessage(err))
    }
  }

  return (
    <div className="container">
      <header className="topbar">
        <h1>我的笔记</h1>
        <div className="topbar-right">
          <span>你好，{user?.username}</span>
          <button onClick={logout}>退出登录</button>
        </div>
      </header>

      <form className="note-form" onSubmit={onSubmit}>
        <h2>{editing ? '编辑笔记' : '新建笔记'}</h2>
        <input
          placeholder="标题"
          value={title}
          onChange={(e) => setTitle(e.target.value)}
          required
        />
        <textarea
          placeholder="内容"
          value={content}
          onChange={(e) => setContent(e.target.value)}
          rows={4}
        />
        {error && <p className="error">{error}</p>}
        <div className="form-actions">
          <button type="submit">{editing ? '保存' : '添加'}</button>
          {editing && (
            <button type="button" className="secondary" onClick={resetForm}>
              取消
            </button>
          )}
        </div>
      </form>

      {loading ? (
        <p className="center">加载中…</p>
      ) : notes.length === 0 ? (
        <p className="empty">还没有笔记，创建第一条吧。</p>
      ) : (
        <ul className="note-list">
          {notes.map((note) => (
            <li key={note.id} className="note-item">
              <div className="note-head">
                <strong>{note.title}</strong>
                <div className="note-actions">
                  <button className="secondary" onClick={() => startEdit(note)}>
                    编辑
                  </button>
                  <button className="danger" onClick={() => remove(note.id)}>
                    删除
                  </button>
                </div>
              </div>
              <p className="note-content">{note.content}</p>
              <small>更新于 {new Date(note.updated_at).toLocaleString()}</small>
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}
