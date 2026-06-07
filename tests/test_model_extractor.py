from src.core.model_extractor import extract_required_models


def test_extracts_vae():
    workflow = {
        "152": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"}
    }
    result = extract_required_models(workflow)
    assert {"folder": "vae", "filename": "ae.safetensors"} in result


def test_extracts_dual_clip():
    workflow = {
        "153": {
            "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "clip_l.safetensors"},
            "class_type": "DualCLIPLoader"
        }
    }
    result = extract_required_models(workflow)
    assert {"folder": "clip", "filename": "t5xxl_fp16.safetensors"} in result
    assert {"folder": "clip", "filename": "clip_l.safetensors"} in result


def test_extracts_unet():
    workflow = {
        "288": {"inputs": {"unet_name": "flux1-dev.safetensors"}, "class_type": "UNETLoader"}
    }
    result = extract_required_models(workflow)
    assert {"folder": "unet", "filename": "flux1-dev.safetensors"} in result


def test_extracts_gguf_unet():
    workflow = {
        "287": {"inputs": {"unet_name": "fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf"}, "class_type": "UnetLoaderGGUF"}
    }
    result = extract_required_models(workflow)
    assert {"folder": "unet", "filename": "fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf"} in result


def test_full_flux_dev_workflow():
    """Mirrors the actual FluxDev.json structure."""
    workflow = {
        "152": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
        "153": {
            "inputs": {"clip_name1": "t5xxl_fp16.safetensors", "clip_name2": "clip_l.safetensors"},
            "class_type": "DualCLIPLoader"
        },
        "287": {"inputs": {"unet_name": "fluxFusionV24StepsGGUFNF4_V2GGUFQ3KM.gguf"}, "class_type": "UnetLoaderGGUF"},
        "288": {"inputs": {"unet_name": "flux1-dev.safetensors"}, "class_type": "UNETLoader"},
    }
    result = extract_required_models(workflow)
    assert len(result) == 5
    folders = {r["folder"] for r in result}
    assert "vae" in folders
    assert "clip" in folders
    assert "unet" in folders


def test_no_duplicates():
    """Same model referenced twice should appear once."""
    workflow = {
        "1": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
        "2": {"inputs": {"vae_name": "ae.safetensors"}, "class_type": "VAELoader"},
    }
    result = extract_required_models(workflow)
    vae_entries = [r for r in result if r["filename"] == "ae.safetensors"]
    assert len(vae_entries) == 1


def test_ignores_linked_inputs():
    """Inputs that are node links (lists) should be ignored, not treated as filenames."""
    workflow = {
        "8": {"inputs": {"vae": ["152", 0]}, "class_type": "VAEDecode"}
    }
    result = extract_required_models(workflow)
    assert result == []


def test_empty_workflow():
    assert extract_required_models({}) == []


def test_checkpoint_loader():
    workflow = {
        "1": {"inputs": {"ckpt_name": "v1-5-pruned.safetensors"}, "class_type": "CheckpointLoaderSimple"}
    }
    result = extract_required_models(workflow)
    assert {"folder": "checkpoints", "filename": "v1-5-pruned.safetensors"} in result


def test_cliploader_flux2_type_maps_to_clip():
    """CLIPLoader with type='flux2' should go to clip/ in standard ComfyUI."""
    workflow = {
        "75:71": {
            "inputs": {
                "clip_name": "qwen_3_8b_fp8mixed.safetensors",
                "type": "flux2",
                "device": "default"
            },
            "class_type": "CLIPLoader"
        }
    }
    result = extract_required_models(workflow)
    assert {"folder": "clip", "filename": "qwen_3_8b_fp8mixed.safetensors"} in result


def test_cliploader_no_type_maps_to_clip():
    """CLIPLoader without a type field defaults to clip/."""
    workflow = {
        "1": {
            "inputs": {"clip_name": "clip_l.safetensors"},
            "class_type": "CLIPLoader"
        }
    }
    result = extract_required_models(workflow)
    assert {"folder": "clip", "filename": "clip_l.safetensors"} in result


def test_dual_clip_flux_type_routes_to_clip():
    """Regression: DualCLIPLoader(type=flux) must put both clip_name1 and clip_name2 in clip/."""
    workflow = {
        "153": {
            "inputs": {
                "clip_name1": "t5xxl_fp16.safetensors",
                "clip_name2": "clip_l.safetensors",
                "type": "flux",
                "device": "default",
            },
            "class_type": "DualCLIPLoader",
        }
    }
    result = extract_required_models(workflow)
    assert {"folder": "clip", "filename": "t5xxl_fp16.safetensors"} in result, \
        "T5 encoder (clip_name1) must go to clip/"
    assert {"folder": "clip", "filename": "clip_l.safetensors"} in result, \
        "CLIP-L (clip_name2) must go to clip/"


def test_kleinedit_workflow():
    """Mirrors the KleinEdit.json structure: CLIPLoader(flux2) + VAELoader."""
    workflow = {
        "75:70": {
            "inputs": {"unet_name": "flux-2-klein-base-9b-fp8.safetensors", "weight_dtype": "default"},
            "class_type": "UNETLoader"
        },
        "75:71": {
            "inputs": {"clip_name": "qwen_3_8b_fp8mixed.safetensors", "type": "flux2", "device": "default"},
            "class_type": "CLIPLoader"
        },
        "75:72": {
            "inputs": {"vae_name": "full_encoder_small_decoder.safetensors"},
            "class_type": "VAELoader"
        },
    }
    result = extract_required_models(workflow)
    folders = {r["folder"]: r["filename"] for r in result}
    assert folders["unet"] == "flux-2-klein-base-9b-fp8.safetensors"
    assert folders["clip"] == "qwen_3_8b_fp8mixed.safetensors", "Qwen model must go to clip/"
    assert folders["vae"] == "full_encoder_small_decoder.safetensors"


def test_extracts_uses_node_folder_cache(monkeypatch):
    """Verifies that extract_required_models prioritizes node_folder_cache ground truth."""
    from src.core import node_folder_cache
    monkeypatch.setattr(node_folder_cache, "_folder_map", {
        "customloader": {
            "model_field": "custom_models_folder"
        }
    })
    workflow = {
        "1": {
            "inputs": {"model_field": "my_special_model.safetensors"},
            "class_type": "CustomLoader"
        }
    }
    result = extract_required_models(workflow)
    assert {"folder": "custom_models_folder", "filename": "my_special_model.safetensors"} in result
