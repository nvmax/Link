
import re
def find_odd_quotes(filename):
    with open(filename, 'r', encoding='utf-8') as f:
        lines = f.readlines()
    
    in_template = False
    for i, line in enumerate(lines, 1):
        # Ignore comments
        line = re.sub(r'//.*', '', line)
        
        counts = line.count('`')
        if counts % 2 != 0:
            print(f"Line {i} has odd backticks ({counts}): {line.strip()}")
            in_template = not in_template

find_odd_quotes('dashboard/src/app/page.tsx')
