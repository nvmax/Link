"""
model_extractor.py

Scans a ComfyUI workflow JSON and returns a deduplicated list of all
model files it requires, along with the ComfyUI models sub-folder each
file belongs in.

Returns a list of dicts:  {"folder": str, "filename": str}

Design philosophy
-----------------
Rather than maintaining an exhaustive hand-written list of every possible
ComfyUI node class, this module uses a **priority-ordered rule engine**:

  Priority 1 – CLIP / text-encoder type detection
      Any node whose class_type contains "clip" (case-insensitive) and
      whose inputs include a "type" field is sent to text_encoders/ if
      the type is a known LLM-encoder architecture, or to clip/ otherwise.
      This single rule covers CLIPLoader, DualCLIPLoader, DualCLIPLoaderGGUF,
      CLIPLoaderGGUF, and any future variant automatically.

  Priority 2 – Input field name semantics
      Certain input field names are unambiguous regardless of the node class:
        • vae_name          → vae/
        • unet_name         → unet/
        • clip_name*        → resolved by type (same as Priority 1)
        • control_net_name  → controlnet/
        • lora_name         → loras/
        • text_encoder*     → text_encoders/
        • ipadapter*        → ipadapter/

  Priority 3 – Node class-type keyword → folder mapping
      Broad substring matches on the lowercased class_type.  Each rule is
      a tuple of (class-type-keywords, field-names, folder).

  Priority 4 – File extension / name heuristics (last resort)
      .gguf files found under a "clip"-named field that weren't already
      resolved are assumed to be LLM text encoders (text_encoders/).
      Checkpoint-like extensions (.safetensors, .ckpt, .pt, .bin) under a
      "ckpt_name" field default to checkpoints/.

New loaders added by custom-node authors are handled automatically by
rules 1–4 without any code changes to this file.
"""

# ---------------------------------------------------------------------------
# Priority 1 & 2 – CLIP-type detection
# ---------------------------------------------------------------------------

# ComfyUI loader 'type' values that indicate an LLM-based text encoder stored
# in models/text_encoders/ rather than models/clip/.
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
    # add new architectures here — no other changes needed
}


def _clip_folder_from_type(inputs: dict) -> str:
    """
    Returns the correct ComfyUI models sub-folder for any CLIP-family loader.

    ComfyUI stores LLM-based text encoders (Qwen, T5, Gemma …) in
    models/text_encoders/ and traditional CLIP models in models/clip/.
    The node's 'type' input field distinguishes them.
    """
    clip_type = (inputs.get("type") or "").lower().strip()
    if clip_type in TEXT_ENCODER_CLIP_TYPES:
        return "text_encoders"
    return "clip"


# ---------------------------------------------------------------------------
# Priority 2 – Input field name → folder (unambiguous, class-independent)
# ---------------------------------------------------------------------------

# Map: input field name prefix/suffix → folder.
# Matched as exact key or via startswith / endswith against the lowercased
# field name.  More specific patterns must come before broader ones.
FIELD_NAME_FOLDER_MAP = [
    # field name (exact or prefix)      folder
    ("vae_name",                        "vae"),
    ("unet_name",                       "unet"),
    ("control_net_name",                "controlnet"),
    ("lora_name",                       "loras"),
    ("ipadapter",                       "ipadapter"),
    ("text_encoder",                    "text_encoders"),   # text_encoder, text_encoder1, text_encoder_1 …
    ("upscale_model",                   "upscale_models"),
    # clip_name* is intentionally OMITTED here — handled by Priority 1
]


def _folder_from_field_name(field: str) -> str | None:
    """Return the folder for a field by name, or None if not deterministic."""
    f = field.lower()
    for prefix, folder in FIELD_NAME_FOLDER_MAP:
        if f == prefix or f.startswith(prefix):
            return folder
    return None


# ---------------------------------------------------------------------------
# Priority 3 – Node class-type keyword → (fields, folder)
# ---------------------------------------------------------------------------
# Each entry: ( [class_type_substrings],  [input_field_names],  folder )
# All matching is case-insensitive substring on the node's class_type.
LOADER_MAP = [
    # Diffusion models / U-Nets
    (["unetloader", "unetloadergguf"],              ["unet_name"],                  "unet"),
    (["diffusionmodelloader"],                      ["model_name", "unet_name"],    "diffusion_models"),

    # Checkpoints
    (["checkpointloadersimple", "checkpointloader"],[["ckpt_name"]],                "checkpoints"),

    # VAE — covers VAELoader, VAELoaderKJ, VAEDecodeTiled, any *VAELoader*
    (["vaeloader"],                                 ["vae_name", "ckpt_name"],      "vae"),
    # LTX Audio VAE and similar: class contains both "vae" and "audio"
    (["audiovaeloader", "audiodecoder"],            ["ckpt_name"],                  "vae"),

    # ControlNet
    (["controlnetloader"],                          ["control_net_name"],           "controlnet"),

    # LoRA
    (["loraloader"],                                ["lora_name"],                  "loras"),

    # Upscale models
    (["upscalemodelloader"],                        ["model_name"],                 "upscale_models"),
    (["latentupscalemodelloader"],                  ["model_name"],                 "latent_upscale_models"),

    # IP-Adapter
    (["ipadaptermodelloader", "ipadapterwithfaceaugment"],
                                                    ["ipadapter", "ipadapter_file"],"ipadapter"),

    # LTX-specific loaders (text encoder projection matrices etc.)
    (["ltxavtextencoderloader"],                    ["text_encoder"],               "text_encoders"),
    (["ltxavtextencoderloader"],                    ["ckpt_name"],                  "checkpoints"),

    # Generic "text encoder" loaders not covered by CLIP family
    (["textencoderloader"],                         ["model_name", "encoder_name"], "text_encoders"),
]


# ---------------------------------------------------------------------------
# Priority 4 – File extension / name heuristics
# ---------------------------------------------------------------------------

def _folder_from_heuristic(field: str, filename: str, class_type_lower: str) -> str | None:
    """
    Last-resort folder inference based on file extension and field/class signals.
    Returns None if no confident inference is possible.
    """
    fn_lower = filename.lower()
    fl_lower = field.lower()

    # .gguf files under a clip-family field → text_encoders (LLM text encoders)
    if fn_lower.endswith(".gguf") and ("clip" in fl_lower or "clip" in class_type_lower):
        return "text_encoders"

    # ckpt_name with no other match → checkpoints
    if fl_lower == "ckpt_name":
        return "checkpoints"

    # vae_name with no other match → vae
    if fl_lower == "vae_name":
        return "vae"

    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def extract_required_models(workflow: dict) -> list[dict]:
    """
    Accepts a ComfyUI workflow dict (the raw JSON loaded as Python dict).

    Returns a deduplicated list of dicts:
        [{"folder": "unet", "filename": "flux1-dev.safetensors"}, ...]

    Only string values are returned; node-link inputs (lists like ["152", 0])
    are ignored automatically.

    The function is forward-compatible: unknown loader nodes are handled
    via field-name semantics and heuristics, not hardcoded class lookups.
    """
    required: list[dict] = []
    seen: set[tuple] = set()

    def _emit(folder: str, filename: str) -> None:
        key = (folder, filename)
        if key not in seen and filename.strip():
            seen.add(key)
            required.append({"folder": folder, "filename": filename})

    for node in workflow.values():
        if not isinstance(node, dict):
            continue

        class_type: str = (node.get("class_type") or "")
        ct_lower = class_type.lower()
        inputs: dict = node.get("inputs") or {}

        # ------------------------------------------------------------------
        # Priority 1 – Any CLIP-family loader: folder determined by 'type'
        # Matches:  CLIPLoader, DualCLIPLoader, DualCLIPLoaderGGUF,
        #           CLIPLoaderGGUF, DualCLIPLoaderADV, …
        # ------------------------------------------------------------------
        if "clip" in ct_lower and "loader" in ct_lower:
            folder = _clip_folder_from_type(inputs)
            for field in ("clip_name", "clip_name1", "clip_name2",
                          "clip_name3", "clip_name4"):
                val = inputs.get(field)
                if isinstance(val, str) and val.strip():
                    _emit(folder, val)
            # Don't continue yet — some dual-loaders also carry a vae_name etc.
            # Fall through to Priority 2 & 3 for other fields on the same node.

        # ------------------------------------------------------------------
        # Priority 2 – Field-name semantics (independent of class_type)
        # ------------------------------------------------------------------
        for field, val in inputs.items():
            if not isinstance(val, str) or not val.strip():
                continue
            fl = field.lower()
            # Skip clip_name* — already handled in Priority 1
            if fl.startswith("clip_name"):
                continue

            folder = _folder_from_field_name(field)
            if folder:
                _emit(folder, val)
                continue

            # ------------------------------------------------------------------
            # Priority 3 – Class-type keyword lookup
            # ------------------------------------------------------------------
            matched = False
            for keywords, fields, kw_folder in LOADER_MAP:
                # Guard: prevent "upscalemodelloader" from matching "latentupscalemodelloader"
                if kw_folder == "upscale_models" and "latent" in ct_lower:
                    continue
                if not any(kw in ct_lower for kw in keywords):
                    continue
                # Normalize the fields spec (may be a nested list from old format)
                flat_fields = fields[0] if (fields and isinstance(fields[0], list)) else fields
                if field in flat_fields:
                    _emit(kw_folder, val)
                    matched = True
                    break

            if matched:
                continue

            # ------------------------------------------------------------------
            # Priority 4 – Heuristic fallback
            # ------------------------------------------------------------------
            folder = _folder_from_heuristic(field, val, ct_lower)
            if folder:
                _emit(folder, val)

    return required
