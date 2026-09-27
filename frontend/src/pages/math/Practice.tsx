import { useState, type ReactNode } from 'react'
import './Practice.css'

interface Question {
  id: number
  title: string
  question: ReactNode
  options: string[]
  correct: number
  correctLabel: string
  steps: string[]
  answer: string
}

const QUESTIONS: Question[] = [
  {
    id: 1,
    title: '例题 1',
    question: (
      <>
        lim<sub>x→0</sub> sinx / x
      </>
    ),
    options: ['0/0 型', '∞/∞ 型', '0·∞ 型'],
    correct: 0,
    correctLabel: '0/0 型',
    steps: ['等价无穷小替换：sinx ~ x', '原式 = lim x/x = 1'],
    answer: '1',
  },
  {
    id: 2,
    title: '例题 2',
    question: (
      <>
        lim<sub>x→∞</sub> (3x<sup>2</sup> + 2x - 1) / (x<sup>2</sup> + 5)
      </>
    ),
    options: ['0/0 型', '∞/∞ 型', '1^∞ 型'],
    correct: 1,
    correctLabel: '∞/∞ 型',
    steps: ['抓大头：分子最高次 3x²，分母最高次 x²', '极限 = 3/1 = 3'],
    answer: '3',
  },
]

/** 单道例题：选题型 → 反馈 → 展示解题步骤（学习互动，不评分） */
function PracticeQuestion({ q }: { q: Question }) {
  const [selected, setSelected] = useState<number | null>(null)
  const isCorrect = selected === q.correct
  const isWrong = selected !== null && !isCorrect

  return (
    <div className="practice-card">
      <div className="practice-head">
        <h3 className="practice-title">{q.title}</h3>
        <div className="practice-question">{q.question}</div>
      </div>

      <p className="practice-step-label">第一步：选择题型类型</p>

      <div className="practice-options">
        {q.options.map((opt, i) => {
          let cls = 'practice-option'
          if (isCorrect && i === q.correct) cls += ' is-correct'
          else if (isWrong && i === selected) cls += ' is-wrong'
          return (
            <button
              key={i}
              className={cls}
              onClick={() => setSelected(i)}
              disabled={isCorrect}
            >
              {opt}
            </button>
          )
        })}
      </div>

      {isCorrect && (
        <div className="practice-feedback practice-feedback-correct">
          <p className="practice-feedback-line">✅ 正确！这是 {q.correctLabel}</p>
          <ol className="practice-steps">
            {q.steps.map((s, i) => (
              <li key={i}>{s}</li>
            ))}
          </ol>
          <div className="practice-answer">答案：{q.answer}</div>
        </div>
      )}

      {isWrong && (
        <div className="practice-feedback practice-feedback-wrong">
          <p className="practice-feedback-line">❌ 再想想</p>
          <p className="practice-correct-answer">正确答案：{q.correctLabel}</p>
        </div>
      )}
    </div>
  )
}

/** 例题练习：先判断题型，再用对应方法解题（内容先静态写死，后续接入数据库） */
export default function Practice() {
  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">例题练习</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">先判断题型，再用对应方法解题</p>
      </header>

      <div className="practice-list">
        {QUESTIONS.map((q) => (
          <PracticeQuestion key={q.id} q={q} />
        ))}
      </div>
    </div>
  )
}
