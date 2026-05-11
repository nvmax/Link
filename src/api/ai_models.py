from pydantic import BaseModel
from typing import List, Dict, Optional

class SystemPrompt(BaseModel):
    id: str
    name: str
    category: str  # 'image' or 'video'
    content: str

class AIProviderConfig(BaseModel):
    base_url: Optional[str] = None
    model: str
    active: bool = False

class AIConfig(BaseModel):
    active_provider: str
    providers: Dict[str, AIProviderConfig]
