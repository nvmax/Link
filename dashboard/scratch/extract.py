import json
import re

log_path = r'C:\Users\Admin\.gemini\antigravity\brain\d04e3b6d-2f4a-4f69-b1a4-13e1c1b1c0d5\.system_generated\logs\overview.txt'
found = False
with open(log_path, 'r', encoding='utf-8') as f:
    for line in f:
        try:
            data = json.loads(line)
            if 'tool_calls' in data:
                for call in data['tool_calls']:
                    if call['name'] in ('replace_file_content', 'multi_replace_file_content', 'write_to_file'):
                        args = call.get('args', {})
                        content = args.get('ReplacementContent', '') or args.get('CodeContent', '')
                        if 'function VisualWorkflowMap' in content:
                            print(f'Found in {call.get("name")}')
                            with open('dashboard/scratch/found_map.txt', 'w', encoding='utf-8') as out:
                                out.write(content)
                            found = True
                    if 'ReplacementChunks' in args:
                        for chunk in json.loads(args['ReplacementChunks']):
                            content = chunk.get('ReplacementContent', '')
                            if 'function VisualWorkflowMap' in content:
                                print(f'Found in {call.get("name")} chunk')
                                with open('dashboard/scratch/found_map.txt', 'w', encoding='utf-8') as out:
                                    out.write(content)
                                found = True
        except Exception as e:
            pass
