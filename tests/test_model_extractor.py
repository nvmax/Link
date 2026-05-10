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
