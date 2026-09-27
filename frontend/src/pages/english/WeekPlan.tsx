import { useEffect, useState } from 'react'
import { Checkbox } from 'antd'
import { getErrorMessage } from '../../api/client'
import { checkTask, getDailyTasks, type DailyTaskItem, type WeekDayTasks } from '../../api/aiTutor'
import './WeekPlan.css'

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 本地日期 → 'YYYY-MM-DD' */
function todayStr(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 'YYYY-MM-DD' → 星期几 */
function weekdayName(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  return WEEKDAY_NAMES[d.getDay()]
}

/** 本周计划：未来 7 天任务列表，今天高亮 */
export default function WeekPlan() {
  const [week, setWeek] = useState<WeekDayTasks[]>([])
  const [error, setError] = useState('')

  useEffect(() => {
    ;(async () => {
      try {
        const res = await getDailyTasks()
        setWeek(res.data.week)
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
  }, [])

  const handleToggle = async (dayDate: string, t: DailyTaskItem) => {
    const next = !t.done
    // 乐观更新，失败回滚
    setWeek((prev) =>
      prev.map((d) =>
        d.date === dayDate
          ? { ...d, tasks: d.tasks.map((x) => (x.type === t.type ? { ...x, done: next } : x)) }
          : d,
      ),
    )
    try {
      await checkTask(dayDate, t.type, next)
    } catch (err) {
      setError(getErrorMessage(err))
      setWeek((prev) =>
        prev.map((d) =>
          d.date === dayDate
            ? { ...d, tasks: d.tasks.map((x) => (x.type === t.type ? { ...x, done: !next } : x)) }
            : d,
        ),
      )
    }
  }

  return (
    <div className="week-plan">
      {week.map((day) => {
        const today = day.date === todayStr()
        return (
          <div
            key={day.date}
            className={today ? 'week-plan-day week-plan-day-today' : 'week-plan-day'}
          >
            <div className="week-plan-day-head">
              <span className="week-plan-day-date">{day.date.slice(5).replace('-', '/')}</span>
              <span className="week-plan-day-week">
                {weekdayName(day.date)}
                {today ? ' · 今天' : ''}
              </span>
            </div>
            <div className="week-plan-day-tasks">
              {day.tasks.map((t) => (
                <label key={t.type} className="week-plan-task">
                  <Checkbox checked={t.done} onChange={() => handleToggle(day.date, t)} />
                  <span
                    className={
                      t.done ? 'week-plan-task-title week-plan-task-title-done' : 'week-plan-task-title'
                    }
                  >
                    {t.title}
                  </span>
                </label>
              ))}
            </div>
          </div>
        )
      })}
      {error && <p className="week-plan-error">{error}</p>}
    </div>
  )
}
