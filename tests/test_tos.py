import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, ServerLimit, UserAgreement
from src.bot.tos import check_tos_agreement

# In-memory SQLite for testing
TEST_DATABASE_URL = "sqlite:///:memory:"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    Base.metadata.create_all(bind=engine)
    with patch("src.database.session.SessionLocal", TestingSessionLocal):
        yield
    Base.metadata.drop_all(bind=engine)

@pytest.mark.anyio
async def test_tos_not_required():
    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890

    # DB setup: server limit has tos_required = False
    db = TestingSessionLocal()
    limit = ServerLimit(guild_id="12345", tos_required=False)
    db.add(limit)
    db.commit()
    db.close()

    result = await check_tos_agreement(interaction)
    assert result is True
    interaction.response.send_message.assert_not_called()

@pytest.mark.anyio
async def test_tos_required_and_user_already_agreed():
    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890

    # DB setup: server limit has tos_required = True, and user has agreed
    db = TestingSessionLocal()
    limit = ServerLimit(guild_id="12345", tos_required=True)
    agreement = UserAgreement(user_id="67890", agreed=True)
    db.add_all([limit, agreement])
    db.commit()
    db.close()

    result = await check_tos_agreement(interaction)
    assert result is True
    interaction.response.send_message.assert_not_called()

@pytest.mark.anyio
async def test_tos_required_and_user_not_agreed():
    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890

    # DB setup: server limit has tos_required = True, but user has not agreed
    db = TestingSessionLocal()
    limit = ServerLimit(guild_id="12345", tos_required=True)
    db.add(limit)
    db.commit()
    db.close()

    result = await check_tos_agreement(interaction)
    assert result is False
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Terms of Service Agreement" in kwargs.get("embed").title
    assert kwargs.get("ephemeral") is True
