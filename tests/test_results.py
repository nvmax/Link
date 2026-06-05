import pytest
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, GenerationJob, JobStatus, Asset
from src.bot.results import ResultHandler

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with patch("src.database.session.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)

class AsyncContextManagerMock:
    async def __aenter__(self):
        f = AsyncMock()
        f.write = AsyncMock()
        return f
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        pass

class MockDiscordFile:
    def __init__(self, fp, filename=None, *args, **kwargs):
        self.filename = filename or os.path.basename(fp)

@pytest.mark.anyio
async def test_handle_execution_done_v1_legacy():
    # 1. Create a dummy job in the DB
    db = TestingSessionLocal()
    job = GenerationJob(
        guild_id="guild_123",
        user_id="user_123",
        workflow_name="test_wf_v1",
        input_params={"prompt": "beautiful sunset"},
        channel_id="111111",
        discord_message_id="222222",
        comfy_prompt_id="prompt_v1",
        status=JobStatus.PROCESSING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # 2. Mock Bot and components
    bot = MagicMock()
    
    # Mock Workflow Registry to return V1 layout config
    mock_workflow = {
        "manifest": {
            "discord": {
                "ui": {
                    "layout_version": "v1",
                    "embed": {
                        "title_template": "{user}'s V1 Generation",
                        "show_metadata": ["prompt"],
                        "show_footer": True,
                        "image_position": "bottom"
                    },
                    "buttons": [
                        {"type": "regenerate", "label": "Redo", "style": "primary"},
                        {"type": "delete", "label": "Remove", "style": "danger"}
                    ]
                }
            }
        }
    }
    bot.workflow_registry.get_workflow.return_value = mock_workflow

    # Mock ComfyUI API Client
    bot.api_client.get_history = AsyncMock(return_value={
        "prompt_v1": {
            "outputs": {
                "9": {
                    "images": [
                        {"filename": "out_v1.png", "subfolder": "", "type": "output"}
                    ]
                }
            }
        }
    })
    bot.api_client.get_image = AsyncMock(return_value=b"fake_image_bytes")
    bot.queue_manager.on_job_completed = AsyncMock()

    # Mock Discord objects
    channel = MagicMock()
    message = AsyncMock()
    channel.fetch_message = AsyncMock(return_value=message)
    bot.get_channel.return_value = channel

    # Mock config assets path and file writing
    with patch("src.core.config.Config.ASSETS_DIR", "/tmp"), \
         patch("aiofiles.open", return_value=AsyncContextManagerMock()), \
         patch("discord.File", MockDiscordFile):
        
        # 3. Instantiate and run ResultHandler
        handler = ResultHandler(bot)
        await handler.handle_execution_done("prompt_v1")

    # 4. Assertions
    # DB status updated
    db = TestingSessionLocal()
    db_job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert db_job.status == JobStatus.COMPLETED
    
    # Verify asset is stored in DB
    asset = db.query(Asset).filter(Asset.job_id == job_id).first()
    assert asset is not None
    assert "out_v1.png" in asset.file_path
    db.close()

    # Verify msg.edit was called with an embed (V1 style)
    message.edit.assert_called_once()
    kwargs = message.edit.call_args[1]
    
    # Check that embed is present, and has correct title
    embed = kwargs.get("embed")
    assert embed is not None
    assert embed.title == "✨ User's V1 Generation"
    assert "Prompt" in embed.description
    
    # Check files/view
    assert len(kwargs.get("attachments")) == 1
    view = kwargs.get("view")
    assert view is not None
    # Verify buttons inside view
    buttons = view.children
    assert len(buttons) == 2
    assert buttons[0].label == "Redo"
    assert buttons[1].label == "Remove"


@pytest.mark.anyio
async def test_handle_execution_done_v2_grid():
    # 1. Create a dummy job in the DB
    db = TestingSessionLocal()
    job = GenerationJob(
        guild_id="guild_123",
        user_id="user_123",
        workflow_name="test_wf_v2",
        input_params={"prompt": "neon city grid", "seed": 42},
        channel_id="111111",
        discord_message_id="222222",
        comfy_prompt_id="prompt_v2",
        status=JobStatus.PROCESSING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # 2. Mock Bot and components
    bot = MagicMock()
    
    # Mock Workflow Registry to return V2 layout config
    mock_workflow = {
        "manifest": {
            "discord": {
                "ui": {
                    "layout_version": "v2",
                    "v2_layout": {
                        "title_template": "{user}'s V2 Generation",
                        "show_metadata": ["prompt", "seed"],
                        "show_footer": True,
                        "media_position": "left",
                        "color": "#ff00ff",
                        "use_role_color": False
                    },
                    "buttons": [
                        {"type": "regenerate", "label": "Re-run", "style": "primary"},
                        {"type": "delete", "label": "Trash", "style": "danger"}
                    ]
                }
            }
        }
    }
    bot.workflow_registry.get_workflow.return_value = mock_workflow

    # Mock ComfyUI API Client
    bot.api_client.get_history = AsyncMock(return_value={
        "prompt_v2": {
            "outputs": {
                "9": {
                    "images": [
                        {"filename": "out_v2.png", "subfolder": "", "type": "output"}
                    ]
                }
            }
        }
    })
    bot.api_client.get_image = AsyncMock(return_value=b"fake_image_bytes")
    bot.queue_manager.on_job_completed = AsyncMock()

    # Mock Discord objects
    channel = MagicMock()
    message = AsyncMock()
    channel.fetch_message = AsyncMock(return_value=message)
    bot.get_channel.return_value = channel

    # Mock config assets path and file writing
    with patch("src.core.config.Config.ASSETS_DIR", "/tmp"), \
         patch("aiofiles.open", return_value=AsyncContextManagerMock()), \
         patch("discord.File", MockDiscordFile):
        
        # 3. Instantiate and run ResultHandler
        handler = ResultHandler(bot)
        await handler.handle_execution_done("prompt_v2")

    # 4. Assertions
    # DB status updated
    db = TestingSessionLocal()
    db_job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert db_job.status == JobStatus.COMPLETED
    db.close()

    # Verify msg.edit was called with embed=None (V2 style) and a LayoutView
    message.edit.assert_called_once()
    kwargs = message.edit.call_args[1]
    
    assert kwargs.get("embed") is None
    
    view = kwargs.get("view")
    assert view is not None
    
    # In discord.py 2.x, LayoutView doesn't inherit from View, but has add_item and children
    # It contains a Container as a child
    from discord.ui import LayoutView, Container, Section, ActionRow
    assert isinstance(view, LayoutView)
    
    # We should have a Container card, and ActionRow(s) for the buttons
    assert len(view.children) >= 2
    container_card = view.children[0]
    assert isinstance(container_card, Container)
    
    # Accent color set correctly
    assert container_card.accent_color == int("ff00ff", 16)
    
    # Check that Container contains a Section since position is left
    assert len(container_card.children) >= 1
    section = container_card.children[0]
    assert isinstance(section, Section)
    
    # Section has accessory (Thumbnail)
    assert section.accessory is not None
    assert getattr(section.accessory.media, "url", section.accessory.media) == "attachment://out_v2.png"
    
    # Section children has title, prompt, metadata
    assert len(section.children) >= 2
    title_text_display = section.children[0]
    assert "V2 Generation" in title_text_display.content
    
    # Verify buttons are added to the layout view
    action_row = view.children[1]
    assert isinstance(action_row, ActionRow)
    assert len(action_row.children) == 2
    assert action_row.children[0].label == "Re-run"
    assert action_row.children[1].label == "Trash"
