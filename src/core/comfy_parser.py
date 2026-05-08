import re
import logging

logger = logging.getLogger(__name__)

def parse_node_list(text: str):
    """
    Parses the output of 'comfy node show installed/all' into a structured list.
    Handles various formats:
    [ ENABLED/DISABLED/UPDATE AVAILABLE ] Display Name
    internal-name (author: author-name) [version]
    """
    if not text:
        return []
        
    output_lines = text.split('\n')
    nodes = []
    current_node = None
    
    # Status regex: matches [ STATUS ] Display Name  [Optionally Name/Extra]
    status_pattern = re.compile(r"\[\s*(?P<status>ENABLED|DISABLED|UPDATE AVAILABLE|NOT INSTALLED|ENABLED\s+\(UPDATE AVAILABLE\))\s*\]\s*(?P<display_name>.+)")
    
    # Metadata regex: matches name (author: author) [version]
    # More flexible: name can be followed by spaces, author/version are optional and author can be empty
    meta_pattern = re.compile(r"^(?P<name>[a-zA-Z0-9_\-\.]+)?(\s*\(author:\s*(?P<author>.*?)\))?(\s*\[(?P<version>.*?)\])?")

    for line in output_lines:
        line = line.strip()
        if not line:
            continue
            
        # Check for a new node entry starting with status
        status_match = status_pattern.search(line)
        if status_match:
            # If we had a previous node, save it
            if current_node:
                nodes.append(current_node)
            
            status = status_match.group("status").strip()
            raw_display = status_match.group("display_name").strip()
            
            # Sometimes the name is on the same line as the display name
            # e.g., "rgthree-comfy  rgthree-comfy"
            parts = re.split(r'\s{2,}', raw_display)
            display_name = parts[0]
            name_guess = parts[1] if len(parts) > 1 else display_name.lower().replace(' ', '-')
            
            current_node = {
                "display_name": display_name,
                "name": name_guess,
                "status": status,
                "author": "Unknown",
                "version": "Unknown",
                "update_available": "UPDATE AVAILABLE" in status
            }
            continue
            
        if current_node:
            # Check if this line has metadata
            # It might start with the name or just (author: ...)
            meta_match = meta_pattern.search(line)
            if meta_match:
                # Update name if matched and we didn't have a good guess
                if meta_match.group("name"):
                    current_node["name"] = meta_match.group("name")
                
                # Update author if matched
                if meta_match.group("author") is not None:
                    author = meta_match.group("author").strip()
                    if author:
                        current_node["author"] = author
                
                # Update version if matched
                if meta_match.group("version"):
                    current_node["version"] = meta_match.group("version").strip()
            
            # Secondary check for update text in any metadata line
            if "update available" in line.lower() or "new version" in line.lower():
                current_node["update_available"] = True

    # Add the last node
    if current_node:
        nodes.append(current_node)
        
    # Final cleanup: ensure unique names (sometimes CLI output has duplicates)
    seen = {}
    unique_nodes = []
    for node in nodes:
        key = f"{node['name']}-{node['author']}"
        if key not in seen:
            seen[key] = True
            unique_nodes.append(node)
            
    return unique_nodes

def parse_snapshot_list(text: str):
    """
    Parses 'comfy node show snapshot-list' output.
    Format:
    - 2024-05-08_12-34-56_snapshot.json
    """
    snapshots = []
    for line in text.split('\n'):
        line = line.strip()
        if line.endswith('.json'):
            # Remove leading bullet or path
            name = line.split('/')[-1].split('\\')[-1].replace('- ', '')
            snapshots.append({
                "id": name,
                "name": name.replace('.json', '')
            })
    return snapshots
