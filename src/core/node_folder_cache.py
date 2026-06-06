"""
node_folder_cache.py

Queries ComfyUI's /object_info API to build an authoritative
(class_type, field_name) → folder_name mapping for every model-picker
input on every registered node.

This is the ground truth — the same data ComfyUI uses internally when
it validates a workflow.  Our heuristics in model_extractor.py exist only
as a fallback for when ComfyUI is offline.

Public API
----------
    await refresh(comfy_url)          # fetch /object_info and populate cache
    get_folder(class_type, field)     # returns folder str or None
    is_stale()                        # True if cache needs refreshing
    clear()                           # invalidate the cache

Cache lifetime
--------------
The cache is held in-process memory.  It is refreshed:
  • On first call to get_folder() when empty
  • Explicitly via refresh() (e.g. on ComfyUI reboot)
  • Automatically after CACHE_TTL_SECONDS if is_stale() is checked
"""

import asyncio
import time
import aiohttp
from typing import Optional
from src.core.logger import setup_logger

logger = setup_logger("node_folder_cache")

# Refresh every 30 minutes.  ComfyUI node list only changes when custom
# nodes are installed / updated, so this is very conservative.
CACHE_TTL_SECONDS = 1800

# ---------------------------------------------------------------------------
# Internal state (module-level singleton — matches the cache.py pattern)
# ---------------------------------------------------------------------------

# {class_type_lower: {field_name_lower: folder}}
_folder_map: dict[str, dict[str, str]] = {}
_fetched_at: float = 0.0          # epoch seconds; 0 means "never"
_refresh_lock = asyncio.Lock()    # prevent thundering herd on first call


# ---------------------------------------------------------------------------
# Parser
# ---------------------------------------------------------------------------

def _parse_object_info(info: dict) -> dict[str, dict[str, str]]:
    """
    Parse the raw /object_info JSON into a nested dict:
        {class_type_lower: {field_name_lower: folder}}

    ComfyUI serialises INPUT_TYPES as:

      "required": {
        "clip_name1": [<file_list_or_combo>, <optional_metadata_dict>],
        "clip_name2": [<file_list_or_combo>, <optional_metadata_dict>],
      }

    The metadata dict may contain:
      {"folder": "text_encoders"}   ← explicit folder name (modern ComfyUI)

    When the folder key is absent we cannot determine the folder from
    object_info alone and return nothing for that field (caller falls
    back to heuristics).

    Some nodes use a nested structure where the first element of the tuple
    is a list of filenames (COMBO inputs from folder_paths).  We detect
    these by checking whether the value is a list whose first element is
    also a list (the filenames).
    """
    result: dict[str, dict[str, str]] = {}

    for class_type, node_data in info.items():
        if not isinstance(node_data, dict):
            continue

        ct_lower = class_type.lower()
        fields: dict[str, str] = {}

        input_schema: dict = node_data.get("input", {})
        for section in ("required", "optional"):
            section_data = input_schema.get(section, {})
            if not isinstance(section_data, dict):
                continue

            for field_name, field_def in section_data.items():
                fl = field_name.lower()

                # field_def should be a list/tuple: [type_or_choices, optional_meta]
                if not isinstance(field_def, (list, tuple)) or len(field_def) == 0:
                    continue

                folder = _extract_folder_from_field_def(field_def)
                if folder:
                    fields[fl] = folder

        if fields:
            result[ct_lower] = fields

    logger.debug(f"Parsed object_info: {len(result)} node types with folder mappings")
    return result


def _extract_folder_from_field_def(field_def: list) -> Optional[str]:
    """
    Extract the folder name from a single field definition tuple.

    Handles two formats:

    Format A — modern ComfyUI with explicit metadata:
        [["file1.safetensors", ...], {"folder": "text_encoders"}]

    Format B — older ComfyUI, no metadata dict, folder inferred from
        the type string (e.g. "MODEL", "VAE", "CLIP"):
        [["file1.safetensors", ...]]   ← no metadata, can't determine folder

    Returns the folder name string, or None if not determinable.
    """
    # Must have at least the first element
    first = field_def[0]

    # Check for explicit metadata dict as second element (Format A)
    if len(field_def) >= 2 and isinstance(field_def[1], dict):
        meta = field_def[1]
        folder = meta.get("folder") or meta.get("folder_name")
        if folder and isinstance(folder, str):
            return folder.strip()

    # Format B — no metadata.  We can still infer for simple type strings.
    # ComfyUI type strings like "MODEL", "VAE", "CLIP" don't carry folder info,
    # but for COMBO inputs (lists of filenames) we cannot know the folder without
    # the metadata key.
    return None


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

async def refresh(comfy_url: str) -> bool:
    """
    Fetch /object_info from ComfyUI and repopulate the cache.

    Returns True on success, False if ComfyUI is unreachable or an error
    occurred (the existing cache is left intact on failure).
    """
    global _folder_map, _fetched_at

    async with _refresh_lock:
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(
                    f"{comfy_url.rstrip('/')}/object_info",
                    timeout=aiohttp.ClientTimeout(total=10),
                ) as resp:
                    if resp.status != 200:
                        logger.warning(
                            f"object_info fetch returned HTTP {resp.status}"
                        )
                        return False
                    raw = await resp.json(content_type=None)

            new_map = _parse_object_info(raw)
            _folder_map = new_map
            _fetched_at = time.monotonic()
            logger.info(
                f"node_folder_cache: refreshed — "
                f"{len(_folder_map)} node types, "
                f"{sum(len(v) for v in _folder_map.values())} field→folder mappings"
            )
            return True

        except aiohttp.ClientConnectorError:
            logger.debug("node_folder_cache: ComfyUI unreachable for object_info fetch")
            return False
        except asyncio.TimeoutError:
            logger.debug("node_folder_cache: object_info fetch timed out")
            return False
        except Exception as exc:
            logger.warning(f"node_folder_cache: unexpected error during refresh: {exc}")
            return False


def get_folder(class_type: str, field_name: str) -> Optional[str]:
    """
    Return the ComfyUI models sub-folder for a given (class_type, field_name)
    pair, or None if the cache has no information.

    Both arguments are matched case-insensitively.
    """
    ct = class_type.lower()
    fl = field_name.lower()
    return _folder_map.get(ct, {}).get(fl)


def get_node_fields(class_type: str) -> dict[str, str]:
    """
    Return all known {field_name: folder} mappings for a class type.
    Returns an empty dict if the node is not in the cache.
    """
    return dict(_folder_map.get(class_type.lower(), {}))


def all_mappings() -> dict[str, dict[str, str]]:
    """Return a snapshot of the entire cache (for the API endpoint)."""
    return {ct: dict(fields) for ct, fields in _folder_map.items()}


def is_stale() -> bool:
    """True if the cache has never been populated or has exceeded its TTL."""
    if _fetched_at == 0.0:
        return True
    return (time.monotonic() - _fetched_at) > CACHE_TTL_SECONDS


def clear() -> None:
    """Invalidate the cache (e.g. after a ComfyUI reboot)."""
    global _folder_map, _fetched_at
    _folder_map = {}
    _fetched_at = 0.0
    logger.info("node_folder_cache: cleared")


async def get_folder_or_refresh(
    class_type: str, field_name: str, comfy_url: str
) -> Optional[str]:
    """
    Convenience helper: return the folder, refreshing the cache first if
    it is stale.  Returns None if ComfyUI is unreachable.
    """
    if is_stale():
        await refresh(comfy_url)
    return get_folder(class_type, field_name)
