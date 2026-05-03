from typing import Optional
from app.agents.base import AgentBase
from app.logging_config import get_logger

logger = get_logger(__name__)


class AgentOrchestrator:
    """Manages all image analysis agents."""
    
    def __init__(self, settings):
        self.settings = settings
        self.agents: dict[str, AgentBase] = {}
        self._running = False
    
    def register(self, agent: AgentBase):
        """Register an agent with the orchestrator."""
        self.agents[agent.name] = agent
        logger.info(f"Registered agent: {agent.name}")
    
    def get_agent(self, name: str) -> Optional[AgentBase]:
        """Get an agent by name."""
        return self.agents.get(name)
    
    def get_all_status(self) -> list[dict]:
        """Get status of all registered agents."""
        return [agent.get_status() for agent in self.agents.values()]
    
    def start_all(self):
        """Start all registered agents."""
        if self._running:
            return
        self._running = True
        for name, agent in self.agents.items():
            try:
                agent.start()
            except Exception as e:
                logger.error(f"Failed to start agent {name}: {e}")
        logger.info(f"Started {len(self.agents)} agents")
    
    def stop_all(self):
        """Stop all registered agents."""
        if not self._running:
            return
        for name, agent in self.agents.items():
            try:
                agent.stop()
            except Exception as e:
                logger.error(f"Failed to stop agent {name}: {e}")
        self._running = False
        logger.info("All agents stopped")
    
    def run_agent(self, name: str) -> bool:
        """Run a specific agent immediately."""
        agent = self.get_agent(name)
        if not agent:
            logger.warning(f"Agent not found: {name}")
            return False
        try:
            agent.run_now()
            return True
        except Exception as e:
            logger.error(f"Failed to run agent {name}: {e}")
            return False
    
    def reset_agent(self, name: str) -> bool:
        """Reset a specific agent's state."""
        agent = self.get_agent(name)
        if not agent:
            return False
        agent.reset()
        return True
