import { useEffect, useRef, useState } from 'react'
import { useParams } from 'react-router-dom'
import chapterHtml from '../../../content/极限章节学习笔记.html?raw'
import ComingSoon from './ComingSoon'
import { READY_CHAPTER_IDS } from './chapters'
import './Notes.css'

/**
 * 知识点梳理：内容由 content/极限章节学习笔记.html 驱动。
 * 用 iframe + srcDoc 隔离渲染：保留原 HTML 自己的样式与折叠脚本，
 * 不被应用全局样式（antd / KaTeX / 页面 CSS）污染，效果与直接打开原 HTML 一致。
 */
export default function Notes() {
  const { chapter } = useParams()
  const iframeRef = useRef<HTMLIFrameElement>(null)
  const [height, setHeight] = useState(1200)

  useEffect(() => {
    const iframe = iframeRef.current
    if (!iframe) return

    let observer: MutationObserver | null = null

    const resize = () => {
      const doc = iframe.contentDocument
      if (!doc) return
      const h = Math.max(
        doc.documentElement.scrollHeight,
        doc.body ? doc.body.scrollHeight : 0,
      )
      setHeight(h)
    }

    const onLoad = () => {
      resize()
      const doc = iframe.contentDocument
      if (doc && doc.body) {
        // 折叠面板开合会改变内容高度，监听 open 属性与子树变化重新量高
        observer = new MutationObserver(resize)
        observer.observe(doc.body, {
          subtree: true,
          childList: true,
          attributes: true,
          attributeFilter: ['open'],
        })
      }
    }

    iframe.addEventListener('load', onLoad)
    // 窗口缩放导致文字换行/表格换行，重新量高
    window.addEventListener('resize', resize)
    return () => {
      iframe.removeEventListener('load', onLoad)
      window.removeEventListener('resize', resize)
      observer?.disconnect()
    }
  }, [])

  if (!READY_CHAPTER_IDS.has(chapter ?? '')) return <ComingSoon chapterId={chapter} />

  return (
    <div className="math-content notes-html">
      <header className="math-content-header">
        <h2 className="math-content-title">知识点梳理</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">高等数学 · 极限章节学习笔记</p>
      </header>

      <iframe
        ref={iframeRef}
        className="notes-html-frame"
        srcDoc={chapterHtml}
        style={{ height }}
        title="高等数学 · 极限章节学习笔记"
      />
    </div>
  )
}
