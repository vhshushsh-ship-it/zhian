import { useEffect, useMemo, useState } from 'react'
import { Calendar, Checkbox, List, Progress, Radio } from 'antd'
import zhCN from 'antd/locale/zh_CN'
import dayjs from 'dayjs'
import 'dayjs/locale/zh-cn'
import { getErrorMessage } from '../../api/client'
import { checkTask, getDailyTasks, refreshPlan, type DailyTaskItem, type WeekDayTasks } from '../../api/aiTutor'
import './Tasks.css'

dayjs.locale('zh-cn')

const WEEKDAY_NAMES = ['周日', '周一', '周二', '周三', '周四', '周五', '周六']

/** 本地日期 → 'YYYY-MM-DD' */
function todayStr(): string {
  const d = new Date()
  const pad = (n: number) => String(n).padStart(2, '0')
  return `${d.getFullYear()}-${pad(d.getMonth() + 1)}-${pad(d.getDate())}`
}

/** 'YYYY-MM-DD' → 星期几 */
function weekdayOf(dateStr: string): string {
  const d = new Date(`${dateStr}T00:00:00`)
  if (Number.isNaN(d.getTime())) return ''
  return WEEKDAY_NAMES[d.getDay()]
}

/** 标题：「9月27日 今天」或「9月28日 周三」 */
function dayTitle(dateStr: string): string {
  const [, m, d] = dateStr.split('-').map(Number)
  const label = dateStr === todayStr() ? '今天' : weekdayOf(dateStr)
  return `${m}月${d}日 ${label}`
}

/** 学习任务页：周视图 / 月视图 + 选中日任务列表 */
export default function Tasks() {
  const [view, setView] = useState<'week' | 'month'>('week')
  const [week, setWeek] = useState<WeekDayTasks[]>([])
  const [selectedDate, setSelectedDate] = useState(todayStr())
  const [error, setError] = useState('')
  const [refreshing, setRefreshing] = useState(false)

  useEffect(() => {
    ;(async () => {
      try {
        const res = await getDailyTasks()
        setWeek(res.data.week)
        setSelectedDate(todayStr())
      } catch (err) {
        setError(getErrorMessage(err))
      }
    })()
  }, [])

  const dayMap = useMemo(() => {
    const m = new Map<string, WeekDayTasks>()
    for (const d of week) m.set(d.date, d)
    return m
  }, [week])

  const selectedTasks = dayMap.get(selectedDate)?.tasks ?? []
  const doneCount = selectedTasks.filter((t) => t.done).length
  const total = selectedTasks.length
  const isToday = selectedDate === todayStr()

  const handleToggle = async (t: DailyTaskItem) => {
    if (!isToday) return
    const next = !t.done
    setWeek((prev) =>
      prev.map((d) =>
        d.date === selectedDate
          ? { ...d, tasks: d.tasks.map((x) => (x.type === t.type ? { ...x, done: next } : x)) }
          : d,
      ),
    )
    try {
      await checkTask(selectedDate, t.type, next)
    } catch (err) {
      setError(getErrorMessage(err))
      setWeek((prev) =>
        prev.map((d) =>
          d.date === selectedDate
            ? { ...d, tasks: d.tasks.map((x) => (x.type === t.type ? { ...x, done: !next } : x)) }
            : d,
        ),
      )
    }
  }

  const handleRefresh = async () => {
    setRefreshing(true)
    setError('')
    try {
      const res = await refreshPlan()
      setWeek(res.data.week)
      setSelectedDate(todayStr())
    } catch (err) {
      setError(getErrorMessage(err))
    } finally {
      setRefreshing(false)
    }
  }

  return (
    <div className="tasks-page">
      <header className="tasks-header">
        <h2 className="tasks-title">学习任务</h2>
        <div className="tasks-header-actions">
          <button
            className="tasks-refresh-btn"
            onClick={handleRefresh}
            disabled={refreshing}
          >
            {refreshing ? 'AI正在调整计划...' : '✨ AI优化计划'}
          </button>
          <Radio.Group
            value={view}
            onChange={(e) => setView(e.target.value)}
            optionType="button"
            buttonStyle="solid"
          >
            <Radio.Button value="week">周视图</Radio.Button>
            <Radio.Button value="month">月视图</Radio.Button>
          </Radio.Group>
        </div>
      </header>

      {error && <p className="tasks-error">{error}</p>}

      {view === 'week' ? (
        <div className="tasks-week">
          {week.map((day) => {
            const done = day.tasks.filter((t) => t.done).length
            const hasTasks = day.tasks.length > 0
            const allDone = hasTasks && done === day.tasks.length
            const today = day.date === todayStr()
            const selected = day.date === selectedDate
            return (
              <button
                key={day.date}
                className={
                  'tasks-day-card' +
                  (today ? ' tasks-day-card-today' : '') +
                  (selected ? ' tasks-day-card-selected' : '')
                }
                onClick={() => setSelectedDate(day.date)}
              >
                <span className="tasks-day-num">{Number(day.date.slice(8))}</span>
                <span className="tasks-day-week">{weekdayOf(day.date)}</span>
                <span className="tasks-day-count">{day.tasks.length}个任务</span>
                <span className={allDone ? 'tasks-day-mark tasks-day-mark-done' : 'tasks-day-mark'}>
                  {allDone ? '✓' : hasTasks ? '•' : ''}
                </span>
              </button>
            )
          })}
        </div>
      ) : (
        <Calendar
          className="tasks-calendar"
          fullscreen={false}
          locale={zhCN.Calendar}
          cellRender={(current, info) => {
            if (info.type !== 'date') return info.originNode
            const dateStr = current.format('YYYY-MM-DD')
            const day = dayMap.get(dateStr)
            if (!day || day.tasks.length === 0) return null
            const allDone = day.tasks.every((t) => t.done)
            return (
              <div className="tasks-cal-cell">
                {allDone ? (
                  <span className="tasks-cal-check">✓</span>
                ) : (
                  <span className="tasks-cal-dot" />
                )}
              </div>
            )
          }}
          onSelect={(current) => setSelectedDate(current.format('YYYY-MM-DD'))}
        />
      )}

      {/* 选中日任务列表 */}
      <section className="tasks-detail">
        <div className="tasks-detail-head">
          <h3 className="tasks-detail-title">{dayTitle(selectedDate)}</h3>
          <Progress
            className="tasks-detail-progress"
            percent={total ? Math.round((doneCount / total) * 100) : 0}
            format={() => `${doneCount}/${total}`}
            size="small"
            strokeColor="#e60012"
          />
        </div>

        {total === 0 ? (
          <p className="tasks-detail-empty">这天暂无任务</p>
        ) : (
          <>
            <List
              className="tasks-detail-list"
              dataSource={selectedTasks}
              renderItem={(t) => (
                <List.Item className="tasks-detail-item">
                  <Checkbox checked={t.done} disabled={!isToday} onChange={() => handleToggle(t)}>
                    <span
                      className={
                        t.done ? 'tasks-detail-text tasks-detail-text-done' : 'tasks-detail-text'
                      }
                    >
                      {t.title}
                    </span>
                  </Checkbox>
                </List.Item>
              )}
            />
            {doneCount === total && (
              <div className="tasks-detail-done">任务全部完成，继续保持！🎉</div>
            )}
          </>
        )}
      </section>
    </div>
  )
}
