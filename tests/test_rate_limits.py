import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timedelta

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, GenerationJob, ServerLimit, UserBan
from src.bot.cogs.generation import GenerationCog

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with patch("src.bot.cogs.generation.SessionLocal", TestingSessionLocal), \
         patch("src.core.queue.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_ban_check_blocks_user():
    bot = MagicMock()
    cog = GenerationCog(bot)

    # Mock Discord interaction for whitelisted server
    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890
    interaction.user.display_name = "banned_user"
    interaction.response.is_done = MagicMock(return_value=False)

    # Insert active ban in test DB
    db = TestingSessionLocal()
    ban = UserBan(
        guild_id="12345",
        user_id="67890",
        username="banned_user",
        ban_type="ban",
        reason="Test violation",
        expires_at=None  # permanent
    )
    db.add(ban)
    db.commit()
    db.close()

    # Call handle_generation_request
    await cog.handle_generation_request(interaction, "some_wf")

    # Verify interaction sent access denied message
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Access Denied" in args[0]
    assert "Test violation" in args[0]

@pytest.mark.anyio
async def test_rate_limit_per_minute_blocks():
    bot = MagicMock()
    cog = GenerationCog(bot)

    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890
    interaction.user.display_name = "test_user"
    interaction.response.is_done = MagicMock(return_value=False)

    # Insert limit of 1 per minute, and insert 1 job already executed within 30s
    db = TestingSessionLocal()
    limit = ServerLimit(
        guild_id="12345",
        rate_limit_per_minute=1,
        rate_limit_per_hour=0,
        quota_per_day=0
    )
    job = GenerationJob(
        guild_id="12345",
        user_id="67890",
        workflow_name="wf",
        status="completed",
        created_at=datetime.utcnow() - timedelta(seconds=10)
    )
    db.add_all([limit, job])
    db.commit()
    db.close()

    # Call handle_generation_request
    await cog.handle_generation_request(interaction, "wf")

    # Verify rate limit warning was sent
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Rate Limited" in args[0]
    assert "per minute" in args[0]

@pytest.mark.anyio
async def test_daily_quota_blocks():
    bot = MagicMock()
    cog = GenerationCog(bot)

    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890
    interaction.user.display_name = "test_user"
    interaction.response.is_done = MagicMock(return_value=False)

    # Limit of 2 per day, with 2 jobs already executed in last 2 hours
    db = TestingSessionLocal()
    limit = ServerLimit(
        guild_id="12345",
        rate_limit_per_minute=0,
        rate_limit_per_hour=0,
        quota_per_day=2
    )
    job1 = GenerationJob(
        guild_id="12345",
        user_id="67890",
        workflow_name="wf",
        status="completed",
        created_at=datetime.utcnow() - timedelta(hours=1)
    )
    job2 = GenerationJob(
        guild_id="12345",
        user_id="67890",
        workflow_name="wf",
        status="completed",
        created_at=datetime.utcnow() - timedelta(hours=2)
    )
    db.add_all([limit, job1, job2])
    db.commit()
    db.close()

    await cog.handle_generation_request(interaction, "wf")

    # Verify daily quota warning was sent
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Quota Exceeded" in args[0]
    assert "daily quota" in args[0]
