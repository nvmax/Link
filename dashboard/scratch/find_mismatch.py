
import re

def find_mismatch_v2(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove strings and comments
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Simple stack for all tags
    stack = []
    
    # Void elements
    voids = {'input', 'img', 'br', 'hr', 'area', 'base', 'col', 'embed', 'link', 'meta', 'param', 'source', 'track', 'wbr'}
    # Components that are self-closing (common ones in this file)
    self_closing_components = {'Settings', 'FileJson', 'ChevronRight', 'Puzzle', 'CheckCircle2', 'Trash2', 'Plus', 'Network', 'Maximize2', 'List', 'ArrowUp', 'ArrowDown', 'Layout', 'Layers', 'Search', 'ExternalLink', 'Eye', 'Type', 'VisualWorkflowMap'}

    # Use regex to find all <tag, </tag, and />
    # We need to distinguish between <Tag /> and <Tag>
    
    pos = 0
    while pos < len(content):
        m = re.search(r'<(/?[a-zA-Z][a-zA-Z0-9]*)', content[pos:])
        if not m: break
        
        tag_start = pos + m.start()
        tag_name = m.group(1)
        
        # Find the end of this tag
        tag_end_match = re.search(r'>', content[tag_start:])
        if not tag_end_match: break
        tag_end = tag_start + tag_end_match.end()
        
        tag_full = content[tag_start:tag_end]
        
        # Check if self-closing
        is_self_closing = tag_full.endswith('/>') or tag_name in voids or tag_name in self_closing_components
        
        if tag_name.startswith('/'):
            t = tag_name[1:]
            if not stack:
                print(f"EXTRA CLOSING </{t}> near {content[tag_start-20:tag_start+20]}")
            else:
                last_tag, last_pos = stack.pop()
                if last_tag != t:
                    print(f"MISMATCH: </{t}> closes <{last_tag}> from pos {last_pos}")
        elif not is_self_closing:
            stack.append((tag_name, tag_start))
            
        pos = tag_end

    print("\nStack at end:")
    for t, p in stack:
        # Get line number for p
        line_no = content[:p].count('\n') + 1
        print(f"Unclosed <{t}> at line {line_no}")

find_mismatch_v2('dashboard/src/app/page.tsx')
