import { useDashboardStore } from '../../store/dashboardStore'

const statusIcons = {
  pending: '\u23F3',
  running: '\u{1F504}',
  completed: '\u2705',
  failed: '\u274C',
  cancelled: '\u26D4',
}

export default function TaskList({ tasks }) {
  const clearCompleted = useDashboardStore((s) => s.clearCompletedTasks)

  if (tasks.length === 0) {
    return <p className="empty-tasks">No tasks in queue</p>
  }

  return (
    <div className="task-list">
      {tasks.slice(0, 10).map((task) => (
        <div key={task.id} className={`task-item task-${task.status}`}>
          <span className="task-icon">{statusIcons[task.status]}</span>
          <div className="task-info">
            <span className="task-type">{task.type}</span>
            <span className="task-desc">{task.description}</span>
          </div>
          <div className="task-progress">
            {task.total_items > 0 ? (
              <div className="progress-bar">
                <div className="progress-fill" style={{ width: `${task.progress}%` }} />
              </div>
            ) : null}
            <span className="task-progress-text">{Math.round(task.progress)}%</span>
          </div>
        </div>
      ))}
      <button className="btn btn-ghost btn-sm" onClick={clearCompleted}>
        Clear Completed
      </button>
    </div>
  )
}
