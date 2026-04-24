
import re

def check_jsx_balance(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    stack = []
    
    for line_num, line in enumerate(lines, 1):
        # Find all <div and </div (simple regex)
        # Note: this ignores comments and strings which is dangerous but good for a start
        tokens = re.findall(r'<(div|/div|main|/main|header|/header)', line)
        
        for token in tokens:
            if token.startswith('/'):
                if not stack:
                    print(f"Extra closing {token} at line {line_num}")
                else:
                    tag, start_line = stack.pop()
                    if tag != token[1:]:
                        print(f"Mismatch: </{token[1:]}> at {line_num} closes <{tag}> from {start_line}")
            else:
                stack.append((token, line_num))
                
    if stack:
        print("\nUnclosed tags:")
        for tag, line in stack:
            print(f"<{tag}> at line {line}")

check_jsx_balance('dashboard/src/app/page.tsx')
