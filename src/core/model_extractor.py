"""
model_extractor.py

Scans a ComfyUI workflow JSON and returns a deduplicated list of all
model files it requires, along with the ComfyUI models sub-folder each
file belongs in.

Returns a list of dicts:  {"folder": str, "filename": str}
"""

# Maps (class_type keywords, input field names, ComfyUI models sub-folder).
# Keywords are matched as substrings of the lowercased class_type value.
LOADER_MAP = [
    (["unetloader", "unetloadergguf"],              ["unet_name"],                  "unet"),
    (["checkpointloadersimple", "checkpointloader"], ["ckpt_name"],                 "checkpoints"),
    (["vaeloader"],                                  ["vae_name"],                  "vae"),
    (["dualcliploader"],                             ["clip_name1", "clip_name2"],  "clip"),
    # NOTE: CLIPLoader is handled separately below — its folder depends on the
    # 'type' input field (LLM-type encoders like flux2/sd3/ltxv go to text_encoders/).
    (["controlnetloader"],                           ["control_net_name"],          "controlnet"),
    (["latentupscalemodelloader"],                   ["model_name"],                "latent_upscale_models"),
    (["upscalemodelloader"],                         ["model_name"],                "upscale_models"),
    # New LTX / Advanced Custom Loaders
    (["ltxavtextencoderloader"],                     ["text_encoder"],               "text_encoders"),
    (["ltxavtextencoderloader"],                     ["ckpt_name"],                  "checkpoints"),
    (["ltxvaudiovaeloader"],                         ["ckpt_name"],                  "vae"),
    (["diffusionmodelloaderkj"],                     ["model_name"],                 "diffusion_models"),
]

# CLIPLoader 'type' values that indicate an LLM-based text encoder stored in
# models/text_encoders/ rather than models/clip/.  ComfyUI's CLIPLoader node
# accepts a 'type' field to distinguish encoder architectures.
TEXT_ENCODER_CLIP_TYPES = {
    "flux",
    "flux2",
    "sd3",
    "ltxv",
    "ltxv2",
    "pixart",
    "stable_audio",
    "cosmos",
    "lumina2",
    "wan",
    "hidream",
    "chroma",
    "ace",
}


def _resolve_clip_loader_folder(inputs: dict) -> str:
    """
    Returns the correct ComfyUI models sub-folder for a CLIPLoader node.

    ComfyUI stores LLM-based text encoders (Qwen, T5, Gemma …) in
    models/text_encoders/ and traditional CLIP models in models/clip/.
    The node's 'type' input field distinguishes them.
    """
    clip_type = (inputs.get("type") or "").lower().strip()
    if clip_type in TEXT_ENCODER_CLIP_TYPES:
        return "text_encoders"
    return "clip"


def extract_required_models(workflow: dict) -> list[dict]:
    """
    Accepts a ComfyUI workflow dict (the raw JSON loaded as Python dict).

    Returns a deduplicated list of dicts:
        [{"folder": "unet", "filename": "flux1-dev.safetensors"}, ...]

    Only string values are returned; node-link inputs (lists like ["152", 0])
    are ignored automatically.
    """
    required: list[dict] = []
    seen: set[tuple] = set()

    for node in workflow.values():
        if not isinstance(node, dict):
            continue

        class_type: str = (node.get("class_type") or "").lower()
        inputs: dict = node.get("inputs") or {}

        # Special case: CLIPLoader folder depends on the 'type' input field.
        if "cliploader" in class_type and "dual" not in class_type:
            val = inputs.get("clip_name")
            if isinstance(val, str) and val.strip():
                folder = _resolve_clip_loader_folder(inputs)
                key = (folder, val)
                if key not in seen:
                    seen.add(key)
                    required.append({"folder": folder, "filename": val})
            continue

        # 1. Standard mapping check
        for keywords, fields, folder in LOADER_MAP:
            # Special case: prevent "upscalemodelloader" from matching "latentupscalemodelloader"
            if folder == "upscale_models" and "latent" in class_type:
                continue

            if not any(kw in class_type for kw in keywords):
                continue

            for field in fields:
                val = inputs.get(field)
                # Only accept plain string filenames — skip node-link lists
                if not isinstance(val, str) or not val.strip():
                    continue

                key = (folder, val)
                if key not in seen:
                    seen.add(key)
                    required.append({"folder": folder, "filename": val})

    return required

