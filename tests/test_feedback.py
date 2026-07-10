import pytest
from unittest.mock import AsyncMock, MagicMock, patch
import discord
import io
from src.bot.cogs.utility import FeedbackModal, FeedbackCategoryView


@pytest.mark.anyio
async def test_feedback_category_view_init():
    bot = MagicMock()
    view = FeedbackCategoryView(bot)
    assert len(view.children) == 1
    assert isinstance(view.category_select, discord.ui.Select)


@pytest.mark.anyio
async def test_feedback_category_view_select():
    bot = MagicMock()
    view = FeedbackCategoryView(bot)
    view.category_select._values = ["Bug"]

    interaction = AsyncMock()
    
    with patch("src.bot.cogs.utility.FeedbackModal") as mock_modal_class:
        mock_modal = MagicMock()
        mock_modal_class.return_value = mock_modal

        await view.select_callback(interaction)

        mock_modal_class.assert_called_once_with(bot, "Bug")
        interaction.response.send_modal.assert_called_once_with(mock_modal)


@pytest.mark.anyio
async def test_feedback_modal_init():
    bot = MagicMock()
    modal = FeedbackModal(bot, "Bug")
    assert modal.title == "Submit Feedback (Bug)"
    assert len(modal.children) == 2
    assert isinstance(modal.note_input, discord.ui.TextInput)
    assert isinstance(modal.file_upload, discord.ui.FileUpload)


@pytest.mark.anyio
async def test_feedback_modal_submit_without_files():
    bot = MagicMock()
    modal = FeedbackModal(bot, "Bug")
    modal.note_input._value = "Test note details"
    modal.file_upload._values = []

    interaction = AsyncMock()
    interaction.guild = MagicMock()
    interaction.guild.id = 123456
    interaction.guild.name = "Test Server"
    interaction.user.id = 99999

    modal.send_feedback = AsyncMock()

    await modal.on_submit(interaction)

    interaction.response.defer.assert_called_once_with(ephemeral=True)
    modal.send_feedback.assert_called_once_with(interaction, "Test note details", [], 123456, "Test Server")


@pytest.mark.anyio
async def test_feedback_modal_submit_feature_request_invalid_file():
    bot = MagicMock()
    modal = FeedbackModal(bot, "Feature Request")
    modal.note_input._value = "Test note details"

    att = MagicMock(spec=discord.Attachment)
    att.filename = "screenshot.png"
    modal.file_upload._values = [att]

    interaction = AsyncMock()
    modal.send_feedback = AsyncMock()

    await modal.on_submit(interaction)

    interaction.response.send_message.assert_called_once_with(
        content="❌ **Error**: Only `.json` files are allowed for Feature Requests. *Please upload your full workflow, not API .json.*",
        ephemeral=True
    )
    interaction.response.defer.assert_not_called()
    modal.send_feedback.assert_not_called()


@pytest.mark.anyio
async def test_feedback_modal_submit_feature_request_valid_json():
    bot = MagicMock()
    modal = FeedbackModal(bot, "Feature Request")
    modal.note_input._value = "Test workflow note"

    att = AsyncMock(spec=discord.Attachment)
    att.filename = "workflow.json"
    att.read = AsyncMock(return_value=b'{"key": "value"}')
    modal.file_upload._values = [att]

    interaction = AsyncMock()
    interaction.guild = MagicMock()
    interaction.guild.id = 123456
    interaction.guild.name = "Test Server"
    interaction.user.id = 99999

    modal.send_feedback = AsyncMock()

    await modal.on_submit(interaction)

    interaction.response.defer.assert_called_once_with(ephemeral=True)
    modal.send_feedback.assert_called_once_with(
        interaction, "Test workflow note", [(b'{"key": "value"}', "workflow.json")], 123456, "Test Server"
    )


@pytest.mark.anyio
async def test_feedback_modal_send_feedback_to_all_admins():
    bot = MagicMock()
    guild = MagicMock()
    guild.id = 123456
    guild.chunked = True

    admin1 = AsyncMock()
    admin1.bot = False
    admin1.guild_permissions.administrator = True
    admin1.id = 11111

    admin2 = AsyncMock()
    admin2.bot = False
    admin2.guild_permissions.administrator = True
    admin2.id = 22222

    bot_member = MagicMock()
    bot_member.bot = True
    bot_member.guild_permissions.administrator = True
    bot_member.id = 33333

    regular_member = MagicMock()
    regular_member.bot = False
    regular_member.guild_permissions.administrator = False
    regular_member.id = 44444

    guild.members = [admin1, admin2, bot_member, regular_member]
    guild.owner = admin1
    guild.owner_id = 11111
    bot.get_guild.return_value = guild

    modal = FeedbackModal(bot, "Bug")
    interaction = AsyncMock()

    with patch("os.path.exists", return_value=False), \
         patch("discord.ui.LayoutView") as mock_layout_view, \
         patch("discord.ui.Container") as mock_container, \
         patch("discord.ui.TextDisplay") as mock_text:

        await modal.send_feedback(interaction, "Test note", [], 123456, "Test Server")

        admin1.send.assert_called_once()
        interaction.edit_original_response.assert_called_with(content="✅ **Feedback sent successfully!** Thank you for your feedback.")


@pytest.mark.anyio
async def test_feedback_modal_send_feedback_with_files():
    bot = MagicMock()
    guild = MagicMock()
    guild.id = 123456
    guild.chunked = True

    admin1 = AsyncMock()
    admin1.bot = False
    admin1.guild_permissions.administrator = True
    admin1.id = 11111

    guild.members = [admin1]
    guild.owner = admin1
    guild.owner_id = 11111
    bot.get_guild.return_value = guild

    modal = FeedbackModal(bot, "Feature Request")
    files_data = [(b'{"workflow": "data"}', "workflow.json")]

    interaction = AsyncMock()

    with patch("os.path.exists", return_value=False), \
         patch("discord.ui.LayoutView") as mock_layout_view, \
         patch("discord.ui.Container") as mock_container, \
         patch("discord.ui.TextDisplay") as mock_text, \
         patch("discord.ui.File") as mock_file:

        await modal.send_feedback(interaction, "Test note", files_data, 123456, "Test Server")

        admin1.send.assert_called_once()
        kwargs = admin1.send.call_args.kwargs
        assert "files" in kwargs
        assert len(kwargs["files"]) == 1
        assert isinstance(kwargs["files"][0], discord.File)
        assert kwargs["files"][0].filename == "workflow.json"
        
        interaction.edit_original_response.assert_called_with(content="✅ **Feedback sent successfully!** Thank you for your feedback.")
