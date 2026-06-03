from fastapi import APIRouter, HTTPException, Request
from src.core.logger import setup_logger
from src.api import state

logger = setup_logger("api_ai")

router = APIRouter()

@router.get("/api/ai/config")
async def get_ai_config():
    return state.ai_service.load_config().dict()

@router.post("/api/ai/config")
async def save_ai_config(request: Request):
    try:
        data = await request.json()
        state.ai_service.save_config(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/api/ai/prompts")
async def get_ai_prompts():
    return [p.dict() for p in state.ai_service.load_prompts()]

@router.post("/api/ai/prompts")
async def save_ai_prompts(request: Request):
    try:
        data = await request.json()
        state.ai_service.save_prompts(data)
        return {"status": "success"}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ai/enhance")
async def enhance_prompt(request: Request):
    data = await request.json()
    user_prompt = data.get("prompt")
    system_prompt_id = data.get("system_prompt_id")
    
    if not user_prompt or not system_prompt_id:
        raise HTTPException(status_code=400, detail="Missing prompt or system_prompt_id")
        
    try:
        enhanced = await state.ai_service.enhance_prompt(user_prompt, system_prompt_id)
        return {"enhanced": enhanced}
    except Exception as e:
        logger.error(f"AI Enhancement failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/api/ai/test")
async def test_ai_connection():
    try:
        response = await state.ai_service.test_connection()
        return {"status": "success", "response": response}
    except Exception as e:
        logger.error(f"AI Test failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))
