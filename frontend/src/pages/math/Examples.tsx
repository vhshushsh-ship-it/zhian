import './Examples.css'

const STEPS: string[] = [
  '代入 x = 0，发现是 0/0 型',
  '用等价无穷小替换：sinx ~ x',
  '原式 = lim x/x = 1',
]

/** 例题精讲：静态示例题（后续接入数据库） */
export default function Examples() {
  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">例题精讲</h2>
        <span className="math-content-accent" aria-hidden="true" />
      </header>

      <div className="example-card">
        <div className="example-question">
          lim<sub>x→0</sub> sinx / x
        </div>

        <ol className="example-steps">
          {STEPS.map((step, i) => (
            <li key={i} className="example-step" data-step={i + 1}>
              {step}
            </li>
          ))}
        </ol>

        <div className="example-answer">
          <span className="example-answer-label">答案</span>
          <span className="example-answer-value">1</span>
        </div>
      </div>

      <p className="example-note">更多例题持续更新中...</p>
    </div>
  )
}
