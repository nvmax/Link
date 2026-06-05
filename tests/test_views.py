import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord

from src.database.models import Base, GenerationJob
from src.bot.views import _execute_chain, handle_smart_action

@pytest.mark.anyio
async def test_execute_chain_attachment_extension_fallback():
    # 1. Mock inputs and target workflow
    target_inputs = [
        {"id": "image", "type": "image_upload", "label": "image", "required": True},
        {"id": "text", "type": "text", "label": "text", "required": True}
    ]
    
    mock_workflow = {
        "manifest": {
            "inputs": target_inputs,
            "workflow_name": "target_wf"
        }
    }
    
    # 2. Mock Bot and components
    bot = MagicMock()
    bot.workflow_registry.get_workflow.return_value = mock_workflow
    
    gen_cog = AsyncMock()
    bot.get_cog.return_value = gen_cog

    # Mock interaction
    interaction = MagicMock()
    interaction.client = bot
    
    # Mock message containing attachment with content_type=None, but filename ending in .png
    message = MagicMock()
    attachment = MagicMock()
    attachment.content_type = None
    attachment.filename = "my_awesome_generation.png"
    attachment.url = "http://discord.cdn/my_awesome_generation.png"
    message.attachments = [attachment]
    
    job = GenerationJob(
        guild_id="guild_1",
        user_id="user_1",
        workflow_name="source_wf",
        input_params={"prompt": "original prompt", "seed": "12345"}
    )

    # 3. Call _execute_chain directly
    with patch("src.bot.views.db_session") as mock_db:
        # DB session mock returns None for asset so it falls back to URL
        mock_session = MagicMock()
        mock_session.query.return_value.filter.return_value.order_by.return_value.first.return_value = None
        mock_db.return_value.__enter__.return_value = mock_session

        await _execute_chain(interaction, job, "target_wf", source_message=message)

    # 4. Assertions
    # Verify handle_generation_request was called with prefilled values
    gen_cog.handle_generation_request.assert_called_once()
    call_args = gen_cog.handle_generation_request.call_args
    prefilled = call_args[1].get("prefilled")
    
    # Check that it successfully mapped the image URL using the extension fallback!
    assert prefilled is not None
    assert prefilled.get("image") == "http://discord.cdn/my_awesome_generation.png"
    assert "text" not in prefilled

@pytest.mark.anyio
async def test_execute_chain_db_asset_lookup():
    # 1. Mock inputs and target workflow
    target_inputs = [
        {"id": "image", "type": "image_upload", "label": "image", "required": True},
        {"id": "text", "type": "text", "label": "text", "required": True}
    ]
    
    mock_workflow = {
        "manifest": {
            "inputs": target_inputs,
            "workflow_name": "target_wf"
        }
    }
    
    # 2. Mock Bot and components
    bot = MagicMock()
    bot.workflow_registry.get_workflow.return_value = mock_workflow
    
    gen_cog = AsyncMock()
    bot.get_cog.return_value = gen_cog

    # Mock interaction
    interaction = MagicMock()
    interaction.client = bot
    
    # Mock message containing NO attachments
    message = MagicMock()
    message.attachments = []
    
    job = GenerationJob(
        id="job_uuid_12345",
        guild_id="guild_1",
        user_id="user_1",
        workflow_name="source_wf",
        input_params={"prompt": "original prompt", "seed": "12345"}
    )

    # Mock asset returned by DB
    mock_asset = MagicMock()
    mock_asset.file_path = "c:/Users/Admin/Desktop/atlas/data/assets/mock_asset.png"
    mock_asset.file_type = "image/png"
    mock_asset.created_at = "2026-06-04T12:00:00"

    # 3. Call _execute_chain directly
    with patch("src.bot.views.db_session") as mock_db, \
         patch("os.path.isfile", return_value=True):
        mock_session = MagicMock()
        
        # When querying assets, return our mock_asset in a list
        mock_session.query.return_value.filter.return_value.order_by.return_value.all.return_value = [mock_asset]
        mock_db.return_value.__enter__.return_value = mock_session

        await _execute_chain(interaction, job, "target_wf", source_message=message)

    # 4. Assertions
    gen_cog.handle_generation_request.assert_called_once()
    call_args = gen_cog.handle_generation_request.call_args
    prefilled = call_args[1].get("prefilled")
    
    # Check that it successfully mapped the image using the database asset path!
    assert prefilled is not None
    assert prefilled.get("image") == "c:/Users/Admin/Desktop/atlas/data/assets/mock_asset.png"
    assert "text" not in prefilled
