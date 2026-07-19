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
from src.api.server import start_api_server

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
    from src.api import state
    state.ws_instance = ws
    
    active_nodes = {}
    last_active_prompt_id = None

    async def progress_handler(packet):
        nonlocal last_active_prompt_id
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id") or packet.get("prompt_id") or last_active_prompt_id
        value = data.get("value")
        max_val = data.get("max")
        node_id = data.get("node")

        if value is not None and max_val is not None and prompt_id:
            node_info = active_nodes.get(prompt_id) or node_id
            logger.info(f"Progress for {prompt_id}: {value}/{max_val} (node={node_info})")
            await result_handler.update_progress(prompt_id, value, max_val, node_type=node_info)

    async def execution_start_handler(packet):
        nonlocal last_active_prompt_id
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id")
        if prompt_id:
            last_active_prompt_id = prompt_id
            active_nodes[prompt_id] = None
            logger.info(f"Execution started for prompt {prompt_id}")

    async def executing_handler(packet):
        """Fires once per node as ComfyUI begins executing it."""
        nonlocal last_active_prompt_id
        data = packet.get("data", {})
        node = data.get("node")
        node_type = data.get("node_type") or data.get("class_type")
        prompt_id = data.get("prompt_id") or packet.get("prompt_id") or last_active_prompt_id

        if node is None:
            # node=None signals the entire prompt finished execution
            if prompt_id:
                logger.info(f"Execution fully finished for prompt {prompt_id}")
                active_nodes.pop(prompt_id, None)
                await result_handler.handle_execution_done(prompt_id)
        else:
            # A new node just started — update the Discord status line
            node_info = node_type or node # Fallback to numeric ID for resolution
            if prompt_id:
                active_nodes[prompt_id] = node_info
                logger.debug(f"Executing node {node} ({node_info}) for prompt {prompt_id}")
                await result_handler.update_node_status(prompt_id, node_info)

    async def execution_success_handler(packet):
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id") or packet.get("prompt_id")
        if prompt_id:
            logger.info(f"execution_success received for prompt {prompt_id}")
            active_nodes.pop(prompt_id, None)
            await result_handler.handle_execution_done(prompt_id)

    async def execution_error_handler(packet):
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id") or packet.get("prompt_id")
        node_id = data.get("node_id", "?")
        node_type = data.get("node_type", "Unknown node")
        exc_message = data.get("exception_message", "An unknown error occurred")
        logger.error(f"ComfyUI execution_error for prompt {prompt_id}: [{node_type}] {exc_message}")
        if prompt_id:
            active_nodes.pop(prompt_id, None)
            await result_handler.handle_execution_error(prompt_id, node_type, exc_message)

    async def execution_interrupted_handler(packet):
        data = packet.get("data", {})
        prompt_id = data.get("prompt_id") or packet.get("prompt_id")
        node_type = data.get("node_type", "Unknown node")
        logger.warning(f"ComfyUI execution_interrupted for prompt {prompt_id} at node {node_type}")
        if prompt_id:
            active_nodes.pop(prompt_id, None)
            await result_handler.handle_execution_error(prompt_id, node_type, "Generation was interrupted.")

    ws.register_handler("execution_start", execution_start_handler)
    ws.register_handler("progress", progress_handler)
    ws.register_handler("executing", executing_handler)
    ws.register_handler("execution_success", execution_success_handler)
    ws.register_handler("execution_error", execution_error_handler)
    ws.register_handler("execution_interrupted", execution_interrupted_handler)

    try:
        # Start WebSocket listener in the background
        ws_task = asyncio.create_task(ws.connect())
        
        # Start Internal API server for Dashboard (port 8001)
        api_task = asyncio.create_task(start_api_server(bot, port=8001))

        # Start Inpaint Activity server for Discord Activities (port 8000 default)
        from src.inpaint.server import start_inpaint_server
        inpaint_task = asyncio.create_task(start_inpaint_server(bot, port=Config.INPAINT_SERVER_PORT))
        
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
    Config.validate_environment()
    Config.ensure_directories()
    asyncio.run(main())
