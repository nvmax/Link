"""
tests/test_node_folder_cache.py

Unit tests for node_folder_cache — verifying that the object_info parser
correctly extracts folder→field mappings, that the cache API works as
expected, and that the integration with models.py resolution priority is
correct.
"""

import pytest
from src.core import node_folder_cache


# ---------------------------------------------------------------------------
# Helpers / fixtures
# ---------------------------------------------------------------------------

def _make_object_info(**nodes) -> dict:
    """
    Build a minimal /object_info response dict.
    Each kwarg is class_type=input_schema where input_schema is a dict
    matching the ComfyUI INPUT_TYPES structure.
    """
    result = {}
    for class_type, input_schema in nodes.items():
        result[class_type] = {"input": input_schema}
    return result


def reset_cache():
    """Ensure the module-level cache is empty before each test."""
    node_folder_cache.clear()


# ---------------------------------------------------------------------------
# Parser tests — modern ComfyUI format (explicit {"folder": ...} metadata)
# ---------------------------------------------------------------------------

class TestParseObjectInfo:
    def setup_method(self):
        reset_cache()

    def test_dual_clip_loader_flux_splits_correctly(self):
        """
        DualCLIPLoader must map clip_name1→text_encoders and clip_name2→clip.
        This is the exact bug that was fixed manually — the cache should
        prevent it from ever needing a manual fix again.
        """
        info = _make_object_info(DualCLIPLoader={
            "required": {
                "clip_name1": [["t5xxl_fp16.safetensors"], {"folder": "text_encoders"}],
                "clip_name2": [["clip_l.safetensors"],     {"folder": "clip"}],
                "type":       [["sdxl", "sd3", "flux", "flux2"]],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["dualcliploader"]["clip_name1"] == "text_encoders"
        assert result["dualcliploader"]["clip_name2"] == "clip"
        # 'type' has no folder metadata — should not appear
        assert "type" not in result.get("dualcliploader", {})

    def test_vae_loader(self):
        info = _make_object_info(VAELoader={
            "required": {
                "vae_name": [["ae.safetensors"], {"folder": "vae"}],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["vaeloader"]["vae_name"] == "vae"

    def test_unet_loader(self):
        info = _make_object_info(UNETLoader={
            "required": {
                "unet_name": [["flux1-dev.safetensors"], {"folder": "diffusion_models"}],
                "weight_dtype": [["default", "fp8_e4m3fn"]],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["unetloader"]["unet_name"] == "diffusion_models"
        assert "weight_dtype" not in result.get("unetloader", {})

    def test_lora_loader(self):
        info = _make_object_info(LoraLoader={
            "required": {
                "lora_name": [["my_lora.safetensors"], {"folder": "loras"}],
                "strength_model": [{"default": 1.0}],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["loraloader"]["lora_name"] == "loras"

    def test_node_with_no_folder_fields_excluded(self):
        """Nodes that only have non-model inputs produce no entry."""
        info = _make_object_info(CLIPTextEncode={
            "required": {
                "text": ["STRING", {"multiline": True}],
                "clip":  ["CLIP"],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        # CLIPTextEncode has no folder-backed inputs
        assert "cliptextencode" not in result

    def test_optional_inputs_are_included(self):
        info = _make_object_info(CheckpointLoaderSimple={
            "required": {},
            "optional": {
                "ckpt_name": [["v1-5-pruned.safetensors"], {"folder": "checkpoints"}],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["checkpointloadersimple"]["ckpt_name"] == "checkpoints"

    def test_folder_name_key_variant(self):
        """Some nodes may use 'folder_name' instead of 'folder' in metadata."""
        info = _make_object_info(SomeLoader={
            "required": {
                "model_name": [["model.safetensors"], {"folder_name": "upscale_models"}],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        assert result["someloader"]["model_name"] == "upscale_models"

    def test_empty_object_info(self):
        assert node_folder_cache._parse_object_info({}) == {}

    def test_case_insensitive_keys(self):
        """Keys are stored lowercase so lookups are case-insensitive."""
        info = _make_object_info(DualCLIPLoaderGGUF={
            "required": {
                "clip_name1": [["t5.gguf"], {"folder": "text_encoders"}],
            }
        })
        result = node_folder_cache._parse_object_info(info)
        # Both the class and field should be stored lowercase
        assert "dualcliploadergguf" in result
        assert "clip_name1" in result["dualcliploadergguf"]

    def test_dynamic_folder_detection(self, tmp_path):
        """Verify dynamic detection of folders by checking existing files on disk."""
        # Setup a mock comfy workspace structure
        comfy_workspace = tmp_path / "ComfyUI"
        models_dir = comfy_workspace / "models"
        clip_dir = models_dir / "clip"
        clip_dir.mkdir(parents=True, exist_ok=True)
        
        # Create a dummy file in models/clip/
        dummy_file = clip_dir / "some_installed_clip.safetensors"
        dummy_file.write_text("dummy content")

        info = _make_object_info(DualCLIPLoader={
            "required": {
                # Format B: Choices list with no metadata dict
                "clip_name1": [["missing_file.safetensors", "some_installed_clip.safetensors"]]
            }
        })

        result = node_folder_cache._parse_object_info(info, comfy_path=str(comfy_workspace))
        assert result["dualcliploader"]["clip_name1"] == "clip"



# ---------------------------------------------------------------------------
# Cache API tests
# ---------------------------------------------------------------------------

class TestCacheAPI:
    def setup_method(self):
        reset_cache()

    def test_get_folder_returns_none_when_empty(self):
        assert node_folder_cache.get_folder("DualCLIPLoader", "clip_name1") is None

    def test_is_stale_when_never_populated(self):
        assert node_folder_cache.is_stale() is True

    def test_get_node_fields_empty(self):
        assert node_folder_cache.get_node_fields("DualCLIPLoader") == {}

    def test_all_mappings_empty(self):
        assert node_folder_cache.all_mappings() == {}

    def test_clear_resets_state(self):
        # Manually poke internal state to simulate a populated cache
        node_folder_cache._folder_map["dualcliploader"] = {
            "clip_name1": "text_encoders",
            "clip_name2": "clip",
        }
        node_folder_cache._fetched_at = 999999.0

        node_folder_cache.clear()

        assert node_folder_cache.is_stale() is True
        assert node_folder_cache.get_folder("DualCLIPLoader", "clip_name1") is None


# ---------------------------------------------------------------------------
# Integration: cache populated → get_folder returns correct answers
# ---------------------------------------------------------------------------

class TestCacheIntegration:
    def setup_method(self):
        reset_cache()
        # Simulate a successful cache refresh by populating internals directly
        node_folder_cache._folder_map = node_folder_cache._parse_object_info(
            _make_object_info(
                DualCLIPLoader={
                    "required": {
                        "clip_name1": [["t5xxl_fp16.safetensors"], {"folder": "text_encoders"}],
                        "clip_name2": [["clip_l.safetensors"],     {"folder": "clip"}],
                    }
                },
                VAELoader={
                    "required": {
                        "vae_name": [["ae.safetensors"], {"folder": "vae"}],
                    }
                },
                UNETLoader={
                    "required": {
                        "unet_name": [["flux1-dev.safetensors"], {"folder": "diffusion_models"}],
                    }
                },
            )
        )
        import time
        node_folder_cache._fetched_at = time.monotonic()

    def test_dual_clip_name1_is_text_encoders(self):
        folder = node_folder_cache.get_folder("DualCLIPLoader", "clip_name1")
        assert folder == "text_encoders", \
            "T5 encoder slot (clip_name1) must resolve to text_encoders/"

    def test_dual_clip_name2_is_clip(self):
        folder = node_folder_cache.get_folder("DualCLIPLoader", "clip_name2")
        assert folder == "clip", \
            "CLIP-L slot (clip_name2) must resolve to clip/"

    def test_vae_name_is_vae(self):
        assert node_folder_cache.get_folder("VAELoader", "vae_name") == "vae"

    def test_unet_name_is_diffusion_models(self):
        assert node_folder_cache.get_folder("UNETLoader", "unet_name") == "diffusion_models"

    def test_case_insensitive_class_lookup(self):
        """get_folder must be case-insensitive on class_type."""
        assert node_folder_cache.get_folder("dualcliploader", "clip_name1") == "text_encoders"
        assert node_folder_cache.get_folder("DUALCLIPLOADER", "clip_name2") == "clip"

    def test_case_insensitive_field_lookup(self):
        """get_folder must be case-insensitive on field_name."""
        assert node_folder_cache.get_folder("VAELoader", "VAE_NAME") == "vae"

    def test_unknown_class_returns_none(self):
        assert node_folder_cache.get_folder("NonExistentNode", "some_field") is None

    def test_unknown_field_returns_none(self):
        assert node_folder_cache.get_folder("VAELoader", "nonexistent_field") is None

    def test_get_node_fields(self):
        fields = node_folder_cache.get_node_fields("DualCLIPLoader")
        assert fields == {"clip_name1": "text_encoders", "clip_name2": "clip"}

    def test_all_mappings_snapshot(self):
        m = node_folder_cache.all_mappings()
        assert "dualcliploader" in m
        assert "vaeloader" in m
        assert m["dualcliploader"]["clip_name1"] == "text_encoders"

    def test_is_not_stale_after_populate(self):
        assert node_folder_cache.is_stale() is False


# ---------------------------------------------------------------------------
# Async refresh tests (mock HTTP)
# ---------------------------------------------------------------------------

class TestAsyncRefresh:
    def setup_method(self):
        reset_cache()

    @pytest.mark.anyio
    async def test_refresh_populates_cache(self, aiohttp_mock=None):
        """
        Simulates a successful /object_info response and verifies the cache
        is populated correctly.  Uses monkeypatching instead of live HTTP.
        """
        import unittest.mock as mock

        fake_object_info = _make_object_info(
            DualCLIPLoader={
                "required": {
                    "clip_name1": [["t5xxl_fp16.safetensors"], {"folder": "text_encoders"}],
                    "clip_name2": [["clip_l.safetensors"], {"folder": "clip"}],
                }
            }
        )

        # Mock aiohttp so no real HTTP is made
        mock_resp = mock.AsyncMock()
        mock_resp.status = 200
        mock_resp.json = mock.AsyncMock(return_value=fake_object_info)
        mock_resp.__aenter__ = mock.AsyncMock(return_value=mock_resp)
        mock_resp.__aexit__ = mock.AsyncMock(return_value=False)

        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(return_value=mock_resp)
        mock_session.__aenter__ = mock.AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = mock.AsyncMock(return_value=False)

        with mock.patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node_folder_cache.refresh("http://127.0.0.1:8188")

        assert result is True
        assert node_folder_cache.get_folder("DualCLIPLoader", "clip_name1") == "text_encoders"
        assert node_folder_cache.get_folder("DualCLIPLoader", "clip_name2") == "clip"
        assert not node_folder_cache.is_stale()

    @pytest.mark.anyio
    async def test_refresh_returns_false_on_connection_error(self):
        import unittest.mock as mock
        import aiohttp

        # Mock the get call to raise a connection error
        mock_session = mock.MagicMock()
        mock_session.get = mock.MagicMock(
            side_effect=aiohttp.ClientConnectorError(
                mock.MagicMock(), OSError("connection refused")
            )
        )
        mock_session.__aenter__ = mock.AsyncMock(return_value=mock_session)
        mock_session.__aexit__ = mock.AsyncMock(return_value=False)

        with mock.patch("aiohttp.ClientSession", return_value=mock_session):
            result = await node_folder_cache.refresh("http://127.0.0.1:8188")

        assert result is False
        assert node_folder_cache.is_stale()

