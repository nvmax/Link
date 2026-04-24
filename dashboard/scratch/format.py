content = open('dashboard/scratch/found_map.txt', encoding='utf-8').read()
content = content.replace('\\n', '\n').replace('\\"', '"')
with open('dashboard/scratch/found_map_pretty.txt', 'w', encoding='utf-8') as f:
    f.write(content)
