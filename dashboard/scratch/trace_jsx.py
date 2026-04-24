
import re

def trace_jsx(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Remove comments
    content = re.sub(r'//.*', '', content)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)
    
    # Track tags with state machine
    stack = []
    voids = {'input', 'img', 'br', 'hr'}
    
    # Find all tags
    # This regex finds <Tag ... /> or <Tag ... > or </Tag>
    # It handles multiline by using DOTALL
    pattern = re.compile(r'<(/?[a-zA-Z][a-zA-Z0-9]*)((?:[^>]*?))(/?)>', re.DOTALL)
    
    for match in pattern.finditer(content):
        tag_name = match.group(1)
        self_closing = match.group(3) == '/'
        
        line_num = content[:match.start()].count('\n') + 1
        
        if tag_name in voids or self_closing:
            continue
            
        if tag_name.startswith('/'):
            t = tag_name[1:]
            if not stack:
                print(f"ERROR: Extra closing </{t}> at line {line_num}")
            else:
                last_tag, start_line = stack.pop()
                if last_tag != t:
                    print(f"ERROR: Mismatch! </{t}> at {line_num} closes <{last_tag}> from {start_line}")
        else:
            # Ignore TS generics in code (often followed by space or comma)
            # A real tag is usually followed by a space, newline, or >
            stack.append((tag_name, line_num))
                
    print("\nFinal stack state:")
    for tag, line in stack:
        print(f"Unclosed <{tag}> from line {line}")

trace_jsx('dashboard/src/app/page.tsx')
