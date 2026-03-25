import json

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

start_idx = content.find('presetTemplates: [')
print(f"Start index: {start_idx}")

if start_idx != -1:
    bracket_count = 0
    end_idx = -1
    for i in range(start_idx + 17, len(content)):
        if content[i] == '[':
            bracket_count += 1
        elif content[i] == ']':
            if bracket_count == 0:
                end_idx = i
                break
            bracket_count -= 1
            
    print(f"End index: {end_idx}")
    if end_idx != -1:
        with open('out.txt', 'w') as f:
            f.write(f"start: {start_idx}, end: {end_idx}")
