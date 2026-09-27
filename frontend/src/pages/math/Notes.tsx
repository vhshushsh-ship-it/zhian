import { useMemo } from 'react'
import Markdown from 'react-markdown'
import remarkMath from 'remark-math'
import rehypeKatex from 'rehype-katex'
import 'katex/dist/katex.min.css'
import chapter1Raw from '../../../content/chapter1-limit.md?raw'
import './Notes.css'

/** 解析后的四级结构（# 章节 / ## 小节 / ### 步骤 / #### 类型） */
interface MdType {
  title: string
  body: string
}

interface MdStep {
  title: string
  body: string
  types: MdType[] | null
}

interface MdSection {
  title: string
  body: string
  steps: MdStep[] | null
}

interface ParsedDoc {
  title: string
  sections: MdSection[]
}

/** 按 # / ## / ### / #### 标题层级切分 Markdown，正文归入最近一级 */
function parseMarkdown(raw: string): ParsedDoc {
  const doc: ParsedDoc = { title: '', sections: [] }
  let section: MdSection | null = null
  let step: MdStep | null = null
  let type: MdType | null = null

  const pushLine = (line: string) => {
    if (type) type.body += (type.body ? '\n' : '') + line
    else if (step) step.body += (step.body ? '\n' : '') + line
    else if (section) section.body += (section.body ? '\n' : '') + line
  }

  for (const line of raw.split(/\r?\n/)) {
    const m = line.match(/^(#{1,4})\s+(.+?)\s*$/)
    if (!m) {
      pushLine(line)
      continue
    }
    const level = m[1].length
    const text = m[2]
    if (level === 1) {
      doc.title = text
      section = null
      step = null
      type = null
    } else if (level === 2) {
      section = { title: text, body: '', steps: null }
      doc.sections.push(section)
      step = null
      type = null
    } else if (level === 3) {
      if (!section) {
        section = { title: '', body: '', steps: [] }
        doc.sections.push(section)
      }
      if (section.steps === null) section.steps = []
      step = { title: text, body: '', types: null }
      section.steps.push(step)
      type = null
    } else {
      // level === 4
      if (!step) {
        if (!section) {
          section = { title: '', body: '', steps: [] }
          doc.sections.push(section)
        }
        if (section.steps === null) section.steps = []
        step = { title: '', body: '', types: [] }
        section.steps.push(step)
      }
      if (step.types === null) step.types = []
      type = { title: text, body: '' }
      step.types.push(type)
    }
  }
  return doc
}

/** 步骤左列标签：把「第一步：先化简」拆成主标题 + 副标题 */
function StepLabel({ title }: { title: string }) {
  const [main, sub] = title.split(/[:：]/)
  return (
    <div className="limit-row-label">
      <span className="limit-row-label-main">{main.trim()}</span>
      {sub && <span className="limit-row-label-sub">{sub.trim()}</span>}
    </div>
  )
}

/** 用 react-markdown 渲染，公式走 KaTeX（$…$ 行内） */
function Md({ source }: { source: string }) {
  return (
    <div className="md">
      <Markdown remarkPlugins={[remarkMath]} rehypePlugins={[rehypeKatex]}>
        {source}
      </Markdown>
    </div>
  )
}

/** 知识点梳理：内容由 content/chapter1-limit.md 驱动（静态解析，后续可换数据库） */
export default function Notes() {
  const doc = useMemo(() => parseMarkdown(chapter1Raw), [])

  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">知识点梳理</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">基础知识点 + 题型方法总结</p>
      </header>

      <section className="notes-chapter">
        {doc.title && <h3 className="notes-chapter-title">{doc.title}</h3>}

        {doc.sections.map((section) =>
          section.steps ? (
            <div className="md-section" key={section.title}>
              <div className="notes-methods-label">{section.title}</div>
              {section.steps.map((step) => (
                <div className="limit-row" key={step.title}>
                  <StepLabel title={step.title} />
                  <div className="limit-row-body">
                    {step.types ? (
                      <div className="type-list">
                        {step.types.map((t) => (
                          <details className="md-details" key={t.title}>
                            <summary>{t.title}</summary>
                            <Md source={t.body} />
                          </details>
                        ))}
                      </div>
                    ) : (
                      <div className="limit-card">
                        <Md source={step.body} />
                      </div>
                    )}
                  </div>
                </div>
              ))}
            </div>
          ) : (
            <details className="md-details" key={section.title}>
              <summary>{section.title}</summary>
              <Md source={section.body} />
            </details>
          ),
        )}
      </section>
    </div>
  )
}
