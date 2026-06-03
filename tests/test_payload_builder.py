import pytest
from src.api.workflows import PayloadBuilder

def test_prune_unreachable_basic():
    # Construct a test template/payload:
    # Node 1: Loader
    # Node 2: KSampler (references Node 1)
    # Node 3: SaveImage (references Node 2) - Terminal Node
    # Node 4: Unconnected Node (should be pruned)
    payload = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {}
        },
        "2": {
            "class_type": "KSampler",
            "inputs": {
                "model": ["1", 0]
            }
        },
        "3": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["2", 0]
            }
        },
        "4": {
            "class_type": "SomeLoader",
            "inputs": {}
        }
    }

    pruned = PayloadBuilder.prune_unreachable(payload)
    
    # 1, 2, 3 should be kept; 4 should be pruned.
    assert "1" in pruned
    assert "2" in pruned
    assert "3" in pruned
    assert "4" not in pruned

def test_prune_unreachable_no_terminal():
    # If no output nodes exist, it should return the original payload
    payload = {
        "1": {
            "class_type": "SomeLoader",
            "inputs": {}
        }
    }
    pruned = PayloadBuilder.prune_unreachable(payload)
    assert "1" in pruned

def test_inject_basic():
    template = {
        "10": {
            "class_type": "CLIPTextEncode",
            "inputs": {
                "text": "original prompt"
            }
        },
        "20": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["10", 0]
            }
        }
    }
    
    manifest = {
        "mapping": {
            "prompt": [["10", "inputs", "text"]]
        }
    }
    
    user_inputs = {
        "prompt": "new enhanced prompt"
    }

    result = PayloadBuilder.inject(template, manifest, user_inputs)
    assert result["10"]["inputs"]["text"] == "new enhanced prompt"

def test_inject_choice_normalization():
    template = {
        "1": {
            "class_type": "EmptyLatentImage",
            "inputs": {
                "width": 512,
                "height": 512
            }
        },
        "2": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["1", 0]
            }
        }
    }
    
    # Manifest has choices for "ratio"
    manifest = {
        "inputs": [
            {
                "id": "ratio",
                "type": "select",
                "choices": ["16:9 Landscape (1024x576)", "1:1 Square (1024x1024)"]
            }
        ],
        "mapping": {
            "ratio": [["1", "inputs", "width"]]
        }
    }
    
    # User sends a stale/cached choice format "9:16 Landscape (1024x576)"
    # It should normalize to "16:9 Landscape (1024x576)"
    user_inputs = {
        "ratio": "9:16 Landscape (1024x576)"
    }

    result = PayloadBuilder.inject(template, manifest, user_inputs)
    assert result["1"]["inputs"]["width"] == "16:9 Landscape (1024x576)"

def test_inject_shared_inputs():
    template = {
        "1": {
            "class_type": "CheckpointLoaderSimple",
            "inputs": {
                "ckpt_name": "sd_xl_base_1.0.safetensors"
            }
        },
        "2": {
            "class_type": "SaveImage",
            "inputs": {
                "images": ["1", 0]
            }
        }
    }
    
    manifest = {
        "inputs": [
            {
                "id": "model",
                "type": "select",
                "choices": "$shared.models"
            }
        ],
        "mapping": {
            "model": [["1", "inputs", "ckpt_name", "filename"]]
        }
    }
    
    shared_inputs = {
        "models": {
            "SDXL Base": {
                "filename": "sd_xl_base_1.0_custom.safetensors"
            }
        }
    }
    
    user_inputs = {
        "model": "SDXL Base"
    }

    result = PayloadBuilder.inject(template, manifest, user_inputs, shared_inputs=shared_inputs)
    assert result["1"]["inputs"]["ckpt_name"] == "sd_xl_base_1.0_custom.safetensors"
