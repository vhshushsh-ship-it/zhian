import './Methods.css'

interface MethodStep {
  title: string
  desc: string
}

const STEPS: MethodStep[] = [
  { title: '先化简', desc: '因式分解 / 有理化 / 等价无穷小替换' },
  { title: '判断类型', desc: '0/0 型、∞/∞ 型、0·∞ 型' },
  { title: '对应方法', desc: '洛必达 / 抓大头 / 泰勒公式' },
]

/** 题型方法：按方法分类，展示固定解法（内容先静态写死，后续接入数据库） */
export default function Methods() {
  return (
    <div className="math-content">
      <header className="math-content-header">
        <h2 className="math-content-title">题型方法</h2>
        <span className="math-content-accent" aria-hidden="true" />
        <p className="math-content-subtitle">按方法分类，每种题型对应固定解法</p>
      </header>

      <div className="methods-card">
        <h3 className="methods-card-title">求极限的 7 种方法</h3>

        <ol className="methods-steps">
          {STEPS.map((step, i) => (
            <li key={i} className="methods-step">
              <span className="methods-step-num">{i + 1}</span>
              <div className="methods-step-body">
                <strong className="methods-step-title">{step.title}</strong>
                <span className="methods-step-desc">{step.desc}</span>
              </div>
            </li>
          ))}
        </ol>
      </div>

      <p className="methods-note">更多方法持续更新中...</p>
    </div>
  )
}
