import os
import json
import yaml
from typing import Dict, Any, List, Optional
from src.core.config import Config
from src.core.logger import setup_logger

logger = setup_logger(__name__)

class WorkflowRegistry:
    def __init__(self, workflows_dir: str = Config.WORKFLOWS_DIR):
        self.workflows_dir = workflows_dir
        self.workflows: Dict[str, Dict[str, Any]] = {}
        self.shared_inputs: Dict[str, Any] = {}
        self.refresh()

    def refresh(self):
        self.workflows = {}
        if not os.path.exists(self.workflows_dir):
            os.makedirs(self.workflows_dir)

        # Load shared inputs first
        shared_path = os.path.join(self.workflows_dir, "shared_inputs.yaml")
        if os.path.exists(shared_path):
            try:
                with open(shared_path, 'r', encoding="utf-8") as f:
                    self.shared_inputs = yaml.safe_load(f) or {}
                logger.info("Loaded shared inputs")
            except Exception as e:
                logger.error(f"Failed to load shared_inputs.yaml: {e}")
            
        for file in os.listdir(self.workflows_dir):
            if file.endswith(".yaml") or file.endswith(".yml"):
                name = os.path.splitext(file)[0]
                json_path = os.path.join(self.workflows_dir, f"{name}.json")
                yaml_path = os.path.join(self.workflows_dir, file)
                
                if os.path.exists(json_path):
                    try:
                        with open(yaml_path, 'r', encoding="utf-8") as y:
                            manifest = yaml.safe_load(y)
                        with open(json_path, 'r', encoding="utf-8") as j:
                            template = json.load(j)
                            
                        self.workflows[name] = {
                            "manifest": self._resolve_shared(manifest),
                            "template": template,
                            "json_path": json_path,
                            "yaml_path": yaml_path
                        }
                        logger.info(f"Loaded workflow: {name}")
                    except Exception as e:
                        logger.error(f"Failed to load workflow {name}: {e}")

    def _resolve_shared(self, manifest: Dict[str, Any]) -> Dict[str, Any]:
        """Resolves $shared references in the manifest."""
        inputs = manifest.get("inputs", [])
        for input_cfg in inputs:
            if isinstance(input_cfg.get("choices"), str) and input_cfg["choices"].startswith("$shared."):
                key = input_cfg["choices"].replace("$shared.", "")
                if key in self.shared_inputs:
                    input_cfg["choices"] = self.shared_inputs[key]
                else:
                    logger.warning(f"Shared reference '{key}' not found in shared_inputs.yaml")
        return manifest

    def get_workflow(self, name: str) -> Optional[Dict[str, Any]]:
        return self.workflows.get(name)

    def list_workflows(self) -> List[str]:
        return list(self.workflows.keys())

class PayloadBuilder:
    @staticmethod
    def inject(template: Dict[str, Any], manifest: Dict[str, Any], user_inputs: Dict[str, Any], shared_inputs: Dict[str, Any] = None) -> Dict[str, Any]:
        logger.info("Building payload...")
        payload = json.loads(json.dumps(template)) # Deep copy
        
        mappings = manifest.get("mapping", {})
        for key, value in user_inputs.items():
            if key in mappings and value is not None and value != "":
                mapping_items = mappings[key]
                logger.info(f"Mapping field: {key} -> {value}")
                
                # Support single mapping or list of mappings
                if not isinstance(mapping_items, list) or len(mapping_items) == 0:
                    continue

                if not isinstance(mapping_items[0], list):
                    mapping_items = [mapping_items]
                
                for path in mapping_items:
                    if len(path) < 3: continue
                    node_id = path[0]
                    field = path[1]
                    sub_field = path[2]
                    attr = path[3] if len(path) > 3 else None
                    
                    if node_id in payload:
                        target_value = value
                        if attr and shared_inputs:
                            for input_cfg in manifest.get("inputs", []):
                                if input_cfg["id"] == key:
                                    # Handle both resolved and unresolved choices
                                    choices = input_cfg.get("choices")
                                    shared_key = None
                                    if isinstance(choices, str) and choices.startswith("$shared."):
                                        shared_key = choices.replace("$shared.", "")
                                    # (Optimization: could store original shared_key in input_cfg)
                                    
                                    if shared_key and shared_key in shared_inputs:
                                        shared_data = shared_inputs[shared_key]
                                        if isinstance(shared_data, dict) and value in shared_data:
                                            target_value = shared_data[value].get(attr, value)
                        
                        logger.info(f"  Injecting {target_value} into node {node_id} ({sub_field})")
                        payload[node_id][field][sub_field] = target_value
                    else:
                        logger.warning(f"Node ID {node_id} not found in template for field {key}")
                    
        logger.info("Payload assembly complete.")
        return PayloadBuilder.prune_unreachable(payload)

    @staticmethod
    def prune_unreachable(payload: Dict[str, Any]) -> Dict[str, Any]:
        """Removes nodes that are not reachable from any terminal (output) node."""
        if not payload:
            return payload

        # 1. Identify all nodes that are referenced as inputs
        referenced_nodes = set()
        for node_data in payload.values():
            for input_val in node_data.get("inputs", {}).values():
                if isinstance(input_val, list) and len(input_val) >= 2:
                    referenced_nodes.add(str(input_val[0]))

        # 2. Terminal nodes are nodes that are NOT referenced by anyone else
        # AND look like they are intended to be outputs (SaveImage, PreviewImage, etc.)
        output_keywords = ["save", "preview", "output", "display", "combine", "vhs", "animation", "video"]
        
        terminal_nodes = []
        for node_id, node_data in payload.items():
            if node_id not in referenced_nodes:
                class_type = node_data.get("class_type", "").lower()
                title = node_data.get("_meta", {}).get("title", "").lower()
                # Check if it looks like an output node
                if any(kw in class_type for kw in output_keywords) or any(kw in title for kw in output_keywords):
                    terminal_nodes.append(node_id)
        
        logger.info(f"Pruning: Found {len(terminal_nodes)} terminal nodes: {terminal_nodes}")
        
        if not terminal_nodes:
            logger.warning("No output nodes found in payload, skipping pruning")
            return payload

        # 3. Traverse backwards from terminal nodes to find all reachable nodes
        reachable = set()
        stack = list(terminal_nodes)
        
        while stack:
            curr_id = stack.pop()
            if curr_id in reachable or curr_id not in payload:
                continue
            
            reachable.add(curr_id)
            node_data = payload[curr_id]
            for input_val in node_data.get("inputs", {}).values():
                if isinstance(input_val, list) and len(input_val) >= 2:
                    stack.append(str(input_val[0]))

        # 4. Filter the payload
        pruned_payload = {node_id: payload[node_id] for node_id in reachable}
        
        removed_ids = [nid for nid in payload if nid not in reachable]
        if removed_ids:
            logger.info(f"Pruned {len(removed_ids)} unreachable nodes: {removed_ids}")
            
        return pruned_payload
