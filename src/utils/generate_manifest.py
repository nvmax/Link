import json
import yaml
import sys
import os

def generate_manifest(json_path, command_name=None):
    if not os.path.exists(json_path):
        print(f"Error: File {json_path} not found.")
        return

    with open(json_path, 'r', encoding="utf-8") as f:
        workflow = json.load(f)

    name = os.path.splitext(os.path.basename(json_path))[0]
    manifest = {
        "workflow_name": name.replace("_", " ").title(),
        "discord_command": command_name or name.replace("_", "").lower(),
        "description": f"High-fidelity generation using {name}",
        "mapping": {},
        "inputs": []
    }

    seen_types = {}

    def sanitize_id(id_str):
        return id_str.replace(":", "_").replace(".", "_").replace("-", "_")

    def get_clean_id(base_type, node_id):
        if base_type not in seen_types:
            seen_types[base_type] = 1
            return base_type
        seen_types[base_type] += 1
        return sanitize_id(f"{base_type}_{node_id}")

    # Common node types to look for
    for node_id, node in workflow.items():
        class_type = node.get("class_type", "")
        inputs = node.get("inputs", {})

        # --- INDEPENDENT FEATURE MAPPING ---
        # We use separate 'if' blocks because one node (like KSampler) might have multiple mappable fields.

        # 1. Identify Prompts
        if class_type in ["CLIPTextEncode", "FluxGuidance"] or "prompt" in inputs or "text" in inputs:
            target_field = "prompt" if "prompt" in inputs else ("text" if "text" in inputs else None)
            if target_field and isinstance(inputs.get(target_field), str):
                field_id = get_clean_id("prompt", node_id)
                manifest["mapping"][field_id] = [node_id, "inputs", target_field]
                # Only add to 'inputs' (Discord parameters) if it's a primary prompt
                if field_id == "prompt" or "text" in field_id:
                    manifest["inputs"].append({
                        "id": field_id,
                        "type": "text_area",
                        "label": "Prompt",
                        "default": inputs[target_field],
                        "required": True
                    })

        # 2. Identify Seeds (Generic Scan)
        seed_fields = [k for k in inputs.keys() if "seed" in k.lower()]
        for target_field in seed_fields:
            field_id = get_clean_id("seed", node_id)
            manifest["mapping"][field_id] = [node_id, "inputs", target_field]
            # Seeds are handled in the background, so we don't add them to manifest["inputs"]

        # 3. Identify Ratio Selectors
        if "Ratio Select" in class_type or class_type == "Empty Latent Ratio Select SDXL":
            target_field = "ratio_selected" if "ratio_selected" in inputs else "ratio"
            if target_field in inputs:
                field_id = get_clean_id("ratio", node_id)
                manifest["mapping"][field_id] = [node_id, "inputs", target_field]
                manifest["inputs"].append({
                    "id": field_id,
                    "type": "select",
                    "label": "Aspect Ratio",
                    "default": inputs[target_field],
                    "choices": "$shared.ratios",
                    "required": False
                })

        # 4. Identify Steps
        if "steps" in inputs and isinstance(inputs["steps"], (int, float)):
            field_id = get_clean_id("steps", node_id)
            manifest["mapping"][field_id] = [node_id, "inputs", "steps"]

        # 5. Identify Image Uploads
        if class_type in ["LoadImage", "ImageScale", "ImageUpscaleWithModel"]:
            target_field = "image" if "image" in inputs else None
            if target_field:
                field_id = get_clean_id("image", node_id)
                manifest["mapping"][field_id] = [node_id, "inputs", target_field]
                manifest["inputs"].append({
                    "id": field_id,
                    "type": "image_upload",
                    "label": "Image",
                    "required": True
                })

        # 6. Identify Audio Uploads
        if class_type in ["LoadAudio", "VHS_LoadAudio"]:
            target_field = "audio" if "audio" in inputs else None
            if target_field:
                field_id = get_clean_id("audio", node_id)
                manifest["mapping"][field_id] = [node_id, "inputs", target_field]
                manifest["inputs"].append({
                    "id": field_id,
                    "type": "audio_upload",
                    "label": "Audio",
                    "required": True
                })

    # Add UI Configuration
    manifest["ui_config"] = {
        "embed": {
            "title_template": "{user}'s Generation",
            "color": "#5865F2",
            "show_metadata": ["prompt", "model", "ratio"]
        },
        "buttons": [
            {"type": "regenerate", "label": "Regenerate", "style": "primary"},
            {"type": "options", "label": "Options", "style": "secondary"},
            {"type": "delete", "label": "Delete", "style": "danger"}
        ]
    }

    # Special logic for FluxDev: Add "Video This" button
    if name.lower() == "fluxdev":
        manifest["ui_config"]["buttons"].append({
            "type": "action",
            "label": "Video This",
            "style": "success",
            "target_workflow": "video",
            "input_mapping": {
                "image": "image"
            }
        })

    # Sort inputs: Put 'prompt' first
    manifest["inputs"].sort(key=lambda x: 0 if x["id"] == "prompt" else 1)

    yaml_path = json_path.replace(".json", ".yaml")
    # Ensure we don't overwrite if it looks like the user has done manual work? 
    # Actually, for now we just overwrite but we've made it much cleaner.
    with open(yaml_path, 'w', encoding="utf-8") as f:
        yaml.dump(manifest, f, sort_keys=False)
    
    print(f"Successfully generated clean manifest: {yaml_path}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Generate a clean YAML manifest from a ComfyUI JSON file.")
    parser.add_argument("json_path", help="Path to the ComfyUI JSON file")
    parser.add_argument("--command", help="The Discord slash command", default=None)
    
    args = parser.parse_args()
    generate_manifest(args.json_path, args.command)
