import unittest
import os
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, GenerationJob, JobStatus
from src.bot.results import ResultHandler

TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

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

class TestResultHandler(unittest.IsolatedAsyncioTestCase):
    def setUp(self):
        Base.metadata.create_all(bind=engine)
        self.db_patcher = patch("src.database.session.SessionLocal", TestingSessionLocal)
        self.db_patcher.start()

    def tearDown(self):
        self.db_patcher.stop()
        Base.metadata.drop_all(bind=engine)

    async def test_handle_execution_done_video_polling(self):
        # 1. Create a dummy job
        db = TestingSessionLocal()
        job = GenerationJob(
            guild_id="guild_123",
            user_id="user_123",
            workflow_name="video_ltx2_5_i2v2",
            input_params={"prompt": "beautiful mountain"},
            channel_id="111111",
            discord_message_id="222222",
            comfy_prompt_id="prompt_video_123",
            status=JobStatus.PROCESSING
        )
        db.add(job)
        db.commit()
        db.close()

        # 2. Mock Bot and API client
        bot = MagicMock()
        bot.workflow_registry.get_workflow.return_value = {
            "manifest": {
                "discord": {
                    "ui": {
                        "layout_version": "v1",
                        "embed": {"title_template": "{user}'s Video"}
                    }
                }
            }
        }
        
        # Simulate ComfyUI returning empty outputs first, then populated outputs on retry
        call_count = 0
        async def mock_get_history(prompt_id):
            nonlocal call_count
            call_count += 1
            if call_count < 2:
                return {prompt_id: {"outputs": {}}}
            return {
                prompt_id: {
                    "outputs": {
                        "75": {
                            "images": [
                                {
                                    "filename": "video_sample.mp4",
                                    "subfolder": "video",
                                    "type": "output"
                                }
                            ]
                        }
                    }
                }
            }
        
        bot.api_client.get_history = mock_get_history
        bot.api_client.get_image = AsyncMock(return_value=b"fake-mp4-data")
        bot.queue_manager = None

        mock_channel = MagicMock()
        mock_msg = AsyncMock()
        mock_channel.fetch_message = AsyncMock(return_value=mock_msg)
        mock_channel.send = AsyncMock()
        bot.get_channel.return_value = mock_channel

        handler = ResultHandler(bot)

        with patch("aiofiles.open", return_value=AsyncContextManagerMock()), \
             patch("discord.File", MockDiscordFile):
            await handler.handle_execution_done("prompt_video_123")

        # Verify retry happened
        self.assertGreaterEqual(call_count, 2)
        # Verify message was edited with the video file
        mock_msg.edit.assert_called_once()
        _, kwargs = mock_msg.edit.call_args
        self.assertEqual(len(kwargs["attachments"]), 1)
        self.assertEqual(kwargs["attachments"][0].filename, "video_sample.mp4")

if __name__ == "__main__":
    unittest.main()
