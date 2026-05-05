import { useEffect } from 'react'
import { useDashboardStore } from '../store/dashboardStore'
import MetricCard from '../components/Dashboard/MetricCard'
import StorageChart from '../components/Dashboard/StorageChart'
import TaskList from '../components/Dashboard/TaskList'
import LogViewer from '../components/Dashboard/LogViewer'

export default function DashboardPage() {
  const { metrics, tasks, logs, loading, error, fetchMetrics, fetchLogs, fetchQueue } = useDashboardStore()

  useEffect(() => {
    fetchMetrics()
    fetchLogs(50)
    fetchQueue()
  }, [])

  if (loading) return <div className="loading-screen">Loading dashboard...</div>
  if (error) return <div className="error-screen">Error: {error}</div>
  if (!metrics) return <div className="empty-dashboard">No data available</div>

  const { performance, storage, system } = metrics

  return (
    <div className="dashboard-page">
      <div className="dashboard-header">
        <h1>Dashboard</h1>
        <span className="dashboard-updated">
          Uptime: {Math.floor(performance.uptime_seconds / 3600)}h {Math.floor((performance.uptime_seconds % 3600) / 60)}m
        </span>
      </div>

      <div className="metrics-grid">
        <MetricCard
          title="App CPU"
          value={`${performance.app_cpu_percent}%`}
          icon="cpu"
          color={performance.app_cpu_percent > 80 ? 'danger' : 'primary'}
        />
        <MetricCard
          title="App Memory"
          value={`${performance.app_memory_mb} MB`}
          subtitle={`${performance.app_memory_percent}% used`}
          icon="memory"
          color={performance.app_memory_percent > 80 ? 'danger' : 'primary'}
        />
        <MetricCard
          title="Photos"
          value={storage.photos.count}
          subtitle={`${storage.photos.size_mb} MB`}
          icon="photo"
          color="success"
        />
        <MetricCard
          title="Thumbnails"
          value={storage.thumbnails.count}
          subtitle={`${storage.thumbnails.size_mb} MB`}
          icon="grid"
          color="info"
        />
        <MetricCard
          title="Disk Usage"
          value={`${storage.disk.percent_used}%`}
          subtitle={`${storage.disk.free_gb} GB free`}
          icon="disk"
          color={storage.disk.percent_used > 90 ? 'danger' : 'warning'}
        />
        <MetricCard
          title="Database"
          value={`${storage.database.size_mb} MB`}
          subtitle={storage.database.type}
          icon="database"
          color="primary"
        />
      </div>

      <div className="dashboard-panels">
        <div className="panel panel-wide">
          <h2>Storage Overview</h2>
          <StorageChart storage={storage} />
        </div>

        <div className="panel">
          <h2>Task Queue</h2>
          <TaskList tasks={tasks} />
        </div>

        <div className="panel panel-wide">
          <h2>Recent Logs</h2>
          <LogViewer logs={logs} />
        </div>

        <div className="panel">
          <h2>System Info</h2>
          <div className="system-info">
            <div className="info-row">
              <span>Platform</span>
              <span>{system.platform}</span>
            </div>
            <div className="info-row">
              <span>Python</span>
              <span>{system.python_version}</span>
            </div>
            <div className="info-row">
              <span>Memory</span>
              <span>{performance.system_memory_total_gb} GB</span>
            </div>
            <div className="info-row">
              <span>System CPU</span>
              <span>{performance.system_cpu_percent}%</span>
            </div>
          </div>
        </div>
      </div>
    </div>
  )
}
