import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, GenerationJob, JobStatus
from src.core.queue import QueueManager

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    # Patch the SessionLocal in queue and generation modules to use our in-memory DB
    with patch("src.core.queue.SessionLocal", TestingSessionLocal), \
         patch("src.bot.cogs.generation.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_queue_adds_and_executes_immediately_when_empty():
    # Setup mock bot and dependencies
    bot = MagicMock()
    bot.client_id = "test_bot_client"
    bot.api_client = AsyncMock()
    bot.api_client.queue_prompt.return_value = "prompt_123"

    queue_manager = QueueManager(bot)
    
    # Mock Discord objects
    channel = AsyncMock()
    message = AsyncMock()
    channel.fetch_message.return_value = message

    # Insert a pending job in our test DB
    db = TestingSessionLocal()
    job = GenerationJob(
        guild_id="guild_1",
        user_id="user_1",
        workflow_name="test_wf",
        input_params={},
        channel_id="channel_1",
        discord_message_id="msg_1",
        status=JobStatus.PENDING
    )
    db.add(job)
    db.commit()
    db.refresh(job)
    job_id = job.id
    db.close()

    # Add the job to queue
    await queue_manager.add_job(
        job_id=job_id,
        payload={"dummy": "data"},
        client_id="test_bot_client",
        channel=channel,
        message_id="msg_1",
        workflow_name="test_wf"
    )

    # Allow async tasks to run (process_next is spawned as a task)
    await asyncio.sleep(0.1)

    # Assert comfy prompt was queued
    bot.api_client.queue_prompt.assert_called_once_with({"dummy": "data"}, "test_bot_client")
    
    # Assert DB state is updated to PROCESSING and comfy_prompt_id set
    db = TestingSessionLocal()
    updated_job = db.query(GenerationJob).filter(GenerationJob.id == job_id).first()
    assert updated_job.status == JobStatus.PROCESSING
    assert updated_job.comfy_prompt_id == "prompt_123"
    db.close()

@pytest.mark.anyio
async def test_queue_multiple_jobs_executes_sequentially():
    bot = MagicMock()
    bot.client_id = "test_bot_client"
    bot.api_client = AsyncMock()
    bot.api_client.queue_prompt.side_effect = ["prompt_1", "prompt_2"]

    queue_manager = QueueManager(bot)
    
    channel = AsyncMock()
    message1 = AsyncMock()
    message2 = AsyncMock()
    
    # Simple message mapping for fetch_message
    async def fetch_message_side_effect(msg_id):
        if msg_id == "msg_1":
            return message1
        elif msg_id == "msg_2":
            return message2
        raise Exception("Message not found")
        
    channel.fetch_message.side_effect = fetch_message_side_effect

    # Create 2 jobs in DB
    db = TestingSessionLocal()
    job1 = GenerationJob(
        guild_id="guild_1", user_id="user_1", workflow_name="wf_1",
        input_params={}, channel_id="channel_1", discord_message_id="msg_1", status=JobStatus.PENDING
    )
    job2 = GenerationJob(
        guild_id="guild_1", user_id="user_2", workflow_name="wf_2",
        input_params={}, channel_id="channel_1", discord_message_id="msg_2", status=JobStatus.PENDING
    )
    db.add_all([job1, job2])
    db.commit()
    db.refresh(job1)
    db.refresh(job2)
    job1_id = job1.id
    job2_id = job2.id
    db.close()

    # Add first job
    await queue_manager.add_job(
        job_id=job1_id, payload={"j": 1}, client_id="test_bot_client",
        channel=channel, message_id="msg_1", workflow_name="wf_1"
    )
    # Add second job (should be queued, not executed immediately)
    await queue_manager.add_job(
        job_id=job2_id, payload={"j": 2}, client_id="test_bot_client",
        channel=channel, message_id="msg_2", workflow_name="wf_2"
    )

    await asyncio.sleep(0.1)

    # First job should have executed, second job is in queue
    assert queue_manager.active_job is not None
    assert queue_manager.active_job["job_id"] == job1_id
    assert len(queue_manager.queue) == 1
    assert queue_manager.queue[0]["job_id"] == job2_id
    
    # Verify second job got queue notice
    message2.edit.assert_called_with(content="⏳ **Queued**: You are at position **#1** in the queue for `wf_2`. Please wait...")

    # Complete first job
    await queue_manager.on_job_completed("prompt_1")
    await asyncio.sleep(0.1)

    # Second job should now be active
    assert queue_manager.active_job is not None
    assert queue_manager.active_job["job_id"] == job2_id
    assert len(queue_manager.queue) == 0

    # Assert Comfy API was called for both
    assert bot.api_client.queue_prompt.call_count == 2
