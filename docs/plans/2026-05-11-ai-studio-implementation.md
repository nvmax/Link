# AI Studio Implementation Plan

> **For Antigravity:** REQUIRED WORKFLOW: Use `.agent/workflows/execute-plan.md` to execute this plan in single-flow mode.

**Goal:** Implement a centralized AI Studio for prompt enhancement with multi-provider support and interactive Discord/Dashboard flows.

**Architecture:** A provider-based backend service (`AiService`) handles LLM calls using `ai_config.yaml` for settings and `prompts.json` for the system prompt library. The Dashboard and Discord Bot consume these via the API to provide interactive prompt enhancement.

**Tech Stack:** FastAPI (Backend), Next.js (Frontend), aiohttp (LLM Requests), Discord.py (Modals).

---

### Task 1: Backend Storage & Models
**Files:**
- Create: `src/api/ai_models.py`
- Create: `src/workflows/prompts.json`
- Create: `src/workflows/ai_config.yaml`

**Step 1: Define data models and initial storage files.**
Create `src/api/ai_models.py`:
```python
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
```

**Step 2: Initialize JSON and YAML storage.**
- `src/workflows/prompts.json`: `[]`
- `src/workflows/ai_config.yaml`:
```yaml
active_provider: "ollama"
providers:
  ollama:
    base_url: "http://127.0.0.1:11434/v1"
    model: "llama3:8b"
    active: true
  openai:
    model: "gpt-4o"
    active: false
```

**Step 3: Commit**
```bash
git add src/api/ai_models.py src/workflows/prompts.json src/workflows/ai_config.yaml
git commit -m "feat(ai): initialize storage and data models"
```

---

### Task 2: AI Provider Service
**Files:**
- Create: `src/api/ai_service.py`

**Step 1: Implement the AiService with provider pattern.**
Create `src/api/ai_service.py`:
```python
import aiohttp
import yaml
import json
import os
from typing import Optional, List
from src.core.config import Config
from src.api.ai_models import AIConfig, SystemPrompt

class AiService:
    def __init__(self):
        self.config_path = os.path.join(Config.WORKFLOWS_DIR, "ai_config.yaml")
        self.prompts_path = os.path.join(Config.WORKFLOWS_DIR, "prompts.json")

    def load_config(self) -> AIConfig:
        if not os.path.exists(self.config_path):
            # Return a default config if file doesn't exist
            return AIConfig(active_provider="ollama", providers={"ollama": {"model": "llama3:8b", "active": True}})
        with open(self.config_path, 'r') as f:
            data = yaml.safe_load(f)
            return AIConfig(**data)

    def load_prompts(self) -> List[SystemPrompt]:
        if not os.path.exists(self.prompts_path): return []
        with open(self.prompts_path, 'r') as f:
            data = json.load(f)
            return [SystemPrompt(**p) for p in data]

    async def enhance_prompt(self, user_prompt: str, system_prompt_id: str) -> str:
        config = self.load_config()
        prompts = self.load_prompts()
        system_prompt = next((p for p in prompts if p.id == system_prompt_id), None)
        
        if not system_prompt:
            raise ValueError(f"System prompt {system_prompt_id} not found")

        provider_id = config.active_provider
        provider_cfg = config.providers.get(provider_id)
        
        # Get API Key from env
        api_key = os.getenv(f"{provider_id.upper()}_API_KEY")
        
        async with aiohttp.ClientSession() as session:
            # Simple OpenAI-compatible implementation as base
            url = f"{provider_cfg.base_url}/chat/completions" if provider_cfg.base_url else "https://api.openai.com/v1/chat/completions"
            headers = {"Authorization": f"Bearer {api_key}"}
            payload = {
                "model": provider_cfg.model,
                "messages": [
                    {"role": "system", "content": system_prompt.content},
                    {"role": "user", "content": user_prompt}
                ]
            }
            async with session.post(url, json=payload, headers=headers) as resp:
                data = await resp.json()
                if resp.status != 200:
                    raise Exception(f"AI Provider error: {data}")
                return data['choices'][0]['message']['content']
```

**Step 2: Commit**
```bash
git add src/api/ai_service.py
git commit -m "feat(ai): implement core AiService"
```

---

### Task 3: Backend API Integration
**Files:**
- Modify: `src/api/server.py`

**Step 1: Register AI endpoints in the FastAPI server.**
- `GET /api/ai/config`
- `POST /api/ai/config`
- `GET /api/ai/prompts`
- `POST /api/ai/prompts`
- `POST /api/ai/enhance`

**Step 2: Run verification**
Start the backend and hit `/api/ai/config` with curl.

**Step 3: Commit**
```bash
git add src/api/server.py
git commit -m "feat(ai): add API endpoints for AI config and prompts"
```

---

### Task 4: Frontend State & Tab
**Files:**
- Modify: `dashboard/src/components/DashboardProvider.tsx`
- Modify: `dashboard/src/app/page.tsx`
- Modify: `dashboard/src/components/Sidebar.tsx`
- Create: `dashboard/src/components/AiStudio.tsx`

**Step 1: Add `aiConfig` and `systemPrompts` to DashboardProvider state.**
**Step 2: Add 'ai-studio' to the activeTab enum.**
**Step 3: Implement the AiStudio tab UI with CRUD for prompts and provider settings.**
**Step 4: Commit**
```bash
git add dashboard/src/components/DashboardProvider.tsx dashboard/src/components/AiStudio.tsx ...
git commit -m "feat(ai): implement AI Studio tab and state management"
```

---

### Task 5: Architect View & Manifest Integration
**Files:**
- Modify: `dashboard/src/components/ArchitectView.tsx`
- Modify: `src/api/workflows.py` (Manifest saving)

**Step 1: Add AI controls (Toggle, Category, Prompt Dropdown) to ArchitectView header.**
**Step 2: Implement "Target Selection" in List View.**
**Step 3: Update manifest saving logic to include `ai_prompt` block.**
**Step 4: Commit**
```bash
git commit -m "feat(ai): integrate AI settings into Architect View and Manifests"
```

---

### Task 6: Discord Bot Enhancement Modal
**Files:**
- Create: `src/bot/modals.py` (AIReviewModal)
- Modify: `src/bot/cogs/generation.py`

**Step 1: Create `AIReviewModal` using `discord.ui.Modal`.**
**Step 2: Intercept `/dream` generation in `GenerationCog`.**
**Step 3: If AI enabled, call `ai_service.enhance_prompt` and show modal.**
**Step 4: Commit**
```bash
git commit -m "feat(ai): implement interactive AI enhancement modal in Discord"
```
