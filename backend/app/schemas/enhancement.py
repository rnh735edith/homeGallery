from pydantic import BaseModel
from typing import Optional, Dict


class EnhancementApplyRequest(BaseModel):
    """Request body for applying enhancement."""
    adjustments: Optional[Dict] = None
    intensity: float = 0.7


class EnhancementSuggestionsResponse(BaseModel):
    """Response for enhancement suggestions."""
    scene_type: Optional[str] = None
    histogram: Optional[Dict] = None
    suggested_adjustments: Dict
    preset_name: str
