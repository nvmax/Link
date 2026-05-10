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
    (["cliploader"],                                 ["clip_name"],                 "clip"),
    (["loraloader", "power lora loader"],            ["lora_name"],                 "loras"),
    (["controlnetloader"],                           ["control_net_name"],          "controlnet"),
    (["upscalemodelloader"],                         ["model_name"],                "upscale_models"),
]


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

        for keywords, fields, folder in LOADER_MAP:
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
