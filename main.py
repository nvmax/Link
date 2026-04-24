import asyncio
import signal
from src.bot.client import LinkBot
from src.database.session import init_db
from src.api.websocket import ComfyWebSocket
from src.bot.results import ResultHandler
from src.core.logger import setup_logger
from src.core.config import Config
from src.api.client import ComfyClient
from src.api.workflows import WorkflowRegistry

logger = setup_logger("main")

async def main():
    # Initialize DB
    init_db()
    logger.info("Database initialized")

    # Initialize Registry and API
    api_client = ComfyClient(Config.COMFY_URL)
    workflow_registry = WorkflowRegistry(Config.WORKFLOWS_DIR)
    
    # Initialize Bot
    bot = LinkBot()
    bot.workflow_registry = workflow_registry
    bot.api_client = api_client
    bot.client_id = api_client.client_id
    
    # Initialize Result Handler
    result_handler = ResultHandler(bot)

    # Initialize WebSocket Listener
    # Use the same client_id as the bot for consistent events
    ws = ComfyWebSocket(Config.COMFY_WS_URL, client_id=bot.client_id)
    
    current_prompt_id = None

    async def progress_handler(packet):
        nonlocal current_prompt_id
        data = packet.get("data", {})
        prompt_id = packet.get("prompt_id") or current_prompt_id
        value = data.get("value")
        max_val = data.get("max")
        
        if value is not None and max_val is not None:
            logger.info(f"Progress for {prompt_id}: {value}/{max_val}")
            await result_handler.update_progress(prompt_id, value, max_val)
 
    async def execution_start_handler(packet):
        nonlocal current_prompt_id
        current_prompt_id = packet.get("data", {}).get("prompt_id")
        logger.info(f"Execution started for prompt {current_prompt_id}")

    async def executed_handler(packet):
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id")
        logger.info(f"Execution finished for prompt {prompt_id}")
        await result_handler.handle_execution_done(prompt_id)

    ws.register_handler("execution_start", execution_start_handler)
    ws.register_handler("progress", progress_handler)
    ws.register_handler("executed", executed_handler)

    try:
        # Start WebSocket listener in the background
        ws_task = asyncio.create_task(ws.connect())
        
        # Start Discord Bot
        await bot.start(Config.DISCORD_TOKEN)
        logger.info("Shutting down...")
    finally:
        if 'ws_task' in locals():
            ws_task.cancel()
        await bot.close()
        if hasattr(ws, 'close'):
            await ws.close()

if __name__ == "__main__":
    asyncio.run(main())
