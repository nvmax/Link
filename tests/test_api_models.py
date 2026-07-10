import pytest
from unittest.mock import AsyncMock, patch
from src.api.routers.models import _check_models_via_comfy_validation

@pytest.mark.anyio
@patch("src.api.routers.models.Config")
@patch("src.api.routers.models.node_folder_cache")
@patch("src.api.routers.models.resolve_comfy_workspace")
@patch("aiohttp.ClientSession.post")
async def test_check_models_via_comfy_validation_with_top_level_error(
    mock_post, mock_resolve, mock_node_cache, mock_config
):
    # Set up mocks
    mock_config.COMFY_URL = "http://fake-comfy"
    mock_resolve.return_value = None
    mock_node_cache.get_folder.return_value = "unet"

    # Simulate response containing both top-level 'error' and 'node_errors'
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "error": {
            "type": "prompt_outputs_failed_validation",
            "message": "Prompt outputs failed validation",
            "details": "",
            "extra_info": {}
        },
        "node_errors": {
            "30:10": {
                "errors": [
                    {
                        "type": "value_not_in_list",
                        "message": "Value not in list",
                        "details": "unet_name: 'krea2_turbo_fp8_scaled.safetensors' not in (list of length 25)",
                        "extra_info": {
                            "input_name": "unet_name",
                            "received_value": "krea2_turbo_fp8_scaled.safetensors"
                        }
                    }
                ],
                "class_type": "UNETLoader"
            }
        }
    }
    
    # Mocking ClientSession.post context manager
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_post.return_value = mock_context

    workflow = {
        "30:10": {
            "inputs": {
                "unet_name": "krea2_turbo_fp8_scaled.safetensors"
            },
            "class_type": "UNETLoader"
        }
    }

    # Execute check
    result = await _check_models_via_comfy_validation(workflow, "http://fake-comfy")

    # Assertions
    assert isinstance(result, list)
    assert len(result) == 1
    assert result[0]["filename"] == "krea2_turbo_fp8_scaled.safetensors"
    assert result[0]["folder"] == "unet"
    assert result[0]["installed"] is False

@pytest.mark.anyio
@patch("src.api.routers.models.Config")
@patch("src.api.routers.models.resolve_comfy_workspace")
@patch("aiohttp.ClientSession.post")
async def test_check_models_via_comfy_validation_propagates_non_model_error(
    mock_post, mock_resolve, mock_config
):
    mock_config.COMFY_URL = "http://fake-comfy"
    mock_resolve.return_value = None

    # Simulate response containing top-level 'error' but no 'node_errors'
    mock_response = AsyncMock()
    mock_response.json.return_value = {
        "error": {
            "type": "missing_node_type",
            "message": "Node 'ID #10' has no class_type. The workflow may be corrupted or a custom node is missing.",
            "details": "Node ID '#10'",
            "extra_info": {"node_id": "10", "class_type": None, "node_title": None}
        }
    }
    
    mock_context = AsyncMock()
    mock_context.__aenter__.return_value = mock_response
    mock_post.return_value = mock_context

    workflow = {}

    result = await _check_models_via_comfy_validation(workflow, "http://fake-comfy")

    assert isinstance(result, dict)
    assert "error" in result
    assert "has no class_type" in result["error"]
