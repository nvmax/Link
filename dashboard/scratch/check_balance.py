
def check_balance(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        content = f.read()
    
    stack = []
    in_string = None
    in_template = False
    
    for i, char in enumerate(content):
        if in_string:
            if char == in_string:
                # Check for escape
                if content[i-1] != '\\':
                    in_string = None
            continue
        
        if in_template:
            if char == '`':
                if content[i-1] != '\\':
                    in_template = False
            continue
            
        if char in ["'", '"']:
            in_string = char
        elif char == '`':
            in_template = True
        elif char == '{':
            stack.append(('{', i))
        elif char == '}':
            if not stack:
                print(f"Extra closing brace at {i}")
            else:
                stack.pop()
                
    
    div_open = content.count('<div')
    div_close = content.count('</div>')
    main_open = content.count('<main')
    main_close = content.count('</main>')
    header_open = content.count('<header')
    header_close = content.count('</header>')
    
    print(f"Div: {div_open} open, {div_close} close")
    print(f"Main: {main_open} open, {main_close} close")
    print(f"Header: {header_open} open, {header_close} close")

check_balance('dashboard/src/app/page.tsx')
