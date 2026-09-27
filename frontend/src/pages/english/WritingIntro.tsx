import { useNavigate } from 'react-router-dom'
import './Writing.css'

/** 写作练习介绍页：学习方法 + 使用说明 + 开始按钮（风格与口语介绍页一致） */
export default function WritingIntro() {
  const navigate = useNavigate()

  return (
    <div className="writing-intro">
      <h2 className="english-content-title">写作练习</h2>
      <span className="english-content-accent" aria-hidden="true" />
      <p className="english-content-intro">AI 批改作文，逐句标注错误，给分与范文一步到位</p>

      <div className="english-detail-card">
        <section className="english-detail-section">
          <h3 className="english-detail-heading">学习方法</h3>
          <ul className="english-detail-list">
            <li>围绕考研、四六级、日常邮件三类话题练笔，从易到难</li>
            <li>AI 老师逐句批改：红色标注原句，绿色给出修改</li>
            <li>语法 40 分 + 结构 30 分 + 用词 30 分，三项分项打分</li>
            <li>每篇附带整体建议与参考范文，写后对照吸收</li>
          </ul>
        </section>
        <section className="english-detail-section">
          <h3 className="english-detail-heading">使用说明</h3>
          <ul className="english-detail-list">
            <li>点击「开始写作」进入练习页</li>
            <li>选择话题分类和难度，系统自动给题，也可自定义题目</li>
            <li>在左侧输入框写下你的作文，实时统计字数</li>
            <li>点击「提交批改」等待 AI 老师返回分数与批改意见</li>
            <li>写作历史自动保存，可随时回看过去的作文</li>
          </ul>
        </section>
      </div>

      <button className="english-start-btn" onClick={() => navigate('/english/writing/practice')}>
        开始写作
      </button>
    </div>
  )
}
