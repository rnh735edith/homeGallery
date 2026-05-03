import api from "../../services/api";

const agentIcons = {
  metadata: "🏷️",
  organization: "📁",
  enhancement: "✨",
  analysis: "📊",
  search: "🔍",
};

export default function AgentCard({ agent, onRefresh }) {
  const icon = agentIcons[agent.name] || "🤖";

  const handleToggle = async () => {
    try {
      if (agent.running) {
        await api.agents.stopAgent(agent.name);
      } else {
        await api.agents.startAgent(agent.name);
      }
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to toggle agent ${agent.name}:`, err);
    }
  };

  const handleRun = async () => {
    try {
      await api.agents.runAgent(agent.name);
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to run agent ${agent.name}:`, err);
    }
  };

  const handleReset = async () => {
    if (
      !window.confirm(
        `Reset ${agent.name} agent? This clears processed counts.`,
      )
    )
      return;
    try {
      await api.agents.resetAgent(agent.name);
      onRefresh?.();
    } catch (err) {
      console.error(`Failed to reset agent ${agent.name}:`, err);
    }
  };

  const formatLastRun = (dateStr) => {
    if (!dateStr) return "Never";
    const date = new Date(dateStr);
    const now = new Date();
    const diffMs = now - date;
    const diffMin = Math.floor(diffMs / 60000);
    if (diffMin < 1) return "Just now";
    if (diffMin < 60) return `${diffMin}m ago`;
    const diffHr = Math.floor(diffMin / 60);
    if (diffHr < 24) return `${diffHr}h ago`;
    return date.toLocaleDateString();
  };

  return (
    <div
      className={`agent-card ${agent.running ? "running" : "stopped"}`}
      data-testid={`agent-card-${agent.name}`}
    >
      <div className="agent-header">
        <span className="agent-icon">{icon}</span>
        <div className="agent-info">
          <h3 className="agent-name">{agent.name}</h3>
          <p className="agent-desc">{agent.description}</p>
        </div>
        <span
          className={`agent-status-dot ${agent.running ? "active" : "inactive"}`}
        >
          {agent.running ? "●" : "○"}
        </span>
      </div>

      <div className="agent-stats">
        <div className="stat">
          <span className="stat-label">Processed</span>
          <span className="stat-value">
            {agent.total_processed?.toLocaleString() || 0}
          </span>
        </div>
        <div className="stat">
          <span className="stat-label">Last Run</span>
          <span className="stat-value">{formatLastRun(agent.last_run)}</span>
        </div>
        <div className="stat">
          <span className="stat-label">Interval</span>
          <span className="stat-value">{agent.interval || 5}min</span>
        </div>
        {agent.errors?.length > 0 && (
          <div className="stat error">
            <span className="stat-label">Errors</span>
            <span className="stat-value">{agent.errors.length}</span>
          </div>
        )}
      </div>

      <div className="agent-actions">
        <button
          className={`btn btn-sm ${agent.running ? "btn-warning" : "btn-primary"}`}
          onClick={handleToggle}
          data-testid={`toggle-agent-${agent.name}`}
        >
          {agent.running ? "Stop" : "Start"}
        </button>
        <button
          className="btn btn-sm btn-secondary"
          onClick={handleRun}
          disabled={agent.running}
          data-testid={`run-agent-${agent.name}`}
        >
          Run Now
        </button>
        <button
          className="btn btn-sm"
          onClick={handleReset}
          data-testid={`reset-agent-${agent.name}`}
        >
          Reset
        </button>
      </div>
    </div>
  );
}
