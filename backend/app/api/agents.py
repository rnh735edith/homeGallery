from fastapi import APIRouter, Depends, HTTPException
from app.utils.security import get_current_admin_user
from app.models.user import User
from app.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(tags=["agents"])

# This will be set by main.py after orchestrator is created
orchestrator = None


@router.get("/agents/status")
def get_all_agents_status(current_user: User = Depends(get_current_admin_user)):
    """Get status of all registered agents."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    return orchestrator.get_all_status()


@router.get("/agents/{name}/status")
def get_agent_status(name: str, current_user: User = Depends(get_current_admin_user)):
    """Get status of a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return agent.get_status()


@router.post("/agents/{name}/start")
def start_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Start a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    agent.start()
    return {"message": f"Agent {name} started"}


@router.post("/agents/{name}/stop")
def stop_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Stop a specific agent."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    agent = orchestrator.get_agent(name)
    if not agent:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    agent.stop()
    return {"message": f"Agent {name} stopped"}


@router.post("/agents/{name}/run")
def run_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Run a specific agent immediately."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    success = orchestrator.run_agent(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return {"message": f"Agent {name} executed"}


@router.post("/agents/{name}/reset")
def reset_agent(name: str, current_user: User = Depends(get_current_admin_user)):
    """Reset a specific agent's state."""
    if not orchestrator:
        raise HTTPException(status_code=503, detail="Agent system not initialized")
    
    success = orchestrator.reset_agent(name)
    if not success:
        raise HTTPException(status_code=404, detail=f"Agent not found: {name}")
    
    return {"message": f"Agent {name} reset"}
