import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from src.database.models import Base, ServerLimit, UserAgreement
from src.bot.tos import check_tos_agreement
from src.database.session import get_db
from src.api.server import app

# Temporary SQLite database for testing
TEST_DATABASE_URL = "sqlite:///test_tos.db"
engine = create_engine(TEST_DATABASE_URL, connect_args={"check_same_thread": False})
TestingSessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

@pytest.fixture(autouse=True)
def setup_test_db():
    import os
    engine.dispose()
    if os.path.exists("test_tos.db"):
        try:
            os.remove("test_tos.db")
        except Exception:
            pass
            
    Base.metadata.create_all(bind=engine)
    
    def override_get_db():
        db = TestingSessionLocal()
        try:
            yield db
        finally:
            db.close()
            
    app.dependency_overrides[get_db] = override_get_db
    
    with patch("src.database.session.SessionLocal", TestingSessionLocal):
        yield
        
    app.dependency_overrides.pop(get_db, None)
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if os.path.exists("test_tos.db"):
        try:
            os.remove("test_tos.db")
        except Exception:
            pass

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

@pytest.mark.anyio
async def test_tos_required_and_user_disagreed():
    interaction = AsyncMock()
    interaction.guild.id = 12345
    interaction.user.id = 67890

    # DB setup: server limit has tos_required = True, and user explicitly disagreed (agreed=False)
    db = TestingSessionLocal()
    limit = ServerLimit(guild_id="12345", tos_required=True)
    agreement = UserAgreement(user_id="67890", agreed=False)
    db.add_all([limit, agreement])
    db.commit()
    db.close()

    result = await check_tos_agreement(interaction)
    assert result is False
    interaction.response.send_message.assert_called_once()
    args, kwargs = interaction.response.send_message.call_args
    assert "Access Denied" in args[0]
    assert kwargs.get("ephemeral") is True

from fastapi.testclient import TestClient

client = TestClient(app)

@pytest.mark.anyio
async def test_api_get_tos_agreements():
    # Mock bot_instance and guild
    bot_mock = MagicMock()
    guild_mock = MagicMock()
    bot_mock.get_guild.return_value = guild_mock
    
    # Mock members
    member1 = MagicMock()
    member1.id = 67890
    member1.name = "agreed_user"
    member1.display_name = "Agreed User"
    member1.avatar = None

    # We mock fetch_members async generator and get_member
    async def mock_fetch_members(limit):
        yield member1

    guild_mock.fetch_members = mock_fetch_members
    guild_mock.get_member.return_value = member1

    # DB setup: server limit has tos_required = True, and user has agreed
    db = TestingSessionLocal()
    limit = ServerLimit(guild_id="12345", tos_required=True)
    agreement = UserAgreement(user_id="67890", agreed=True)
    db.add_all([limit, agreement])
    db.commit()
    db.close()

    from src.api import state
    with patch.object(state, "bot_instance", bot_mock), \
         patch("src.core.config.Config.API_KEY", None):
        response = client.get("/api/discord/guild/12345/tos-agreements")
        assert response.status_code == 200
        data = response.json()
        assert "agreements" in data
        assert len(data["agreements"]) == 1
        assert data["agreements"][0]["user_id"] == "67890"
        assert data["agreements"][0]["username"] == "agreed_user"
        assert data["agreements"][0]["agreed"] is True

@pytest.mark.anyio
async def test_api_delete_tos_agreement():
    # DB setup: insert agreement
    db = TestingSessionLocal()
    agreement = UserAgreement(user_id="67890", agreed=True)
    db.add(agreement)
    db.commit()
    db.close()

    # Call delete API
    with patch("src.core.config.Config.API_KEY", None):
        response = client.delete("/api/discord/tos-agreements/67890")
    assert response.status_code == 200
    assert response.json()["status"] == "success"

    # Verify deleted from DB
    db = TestingSessionLocal()
    ag = db.query(UserAgreement).filter(UserAgreement.user_id == "67890").first()
    assert ag is None
    db.close()
