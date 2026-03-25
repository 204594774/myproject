import json

# (Paste the presets here, omitting the large block for brevity, I will read it from update_presets2.py)
with open('update_presets2.py', 'r', encoding='utf-8') as f:
    py_code = f.read()

# Execute the code from update_presets2 to get the presets variable
exec(py_code[:py_code.find('with open')])

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    lines = f.readlines()

start_idx = -1
end_idx = -1

for i, line in enumerate(lines):
    if 'presetTemplates: [' in line:
        start_idx = i
    if start_idx != -1 and i > start_idx and 'compForm: {' in line:
        end_idx = i - 1
        break

if start_idx != -1 and end_idx != -1:
    # replace lines
    new_json = json.dumps(presets, indent=4, ensure_ascii=False)
    # indent properly
    indented_json = '\n'.join('            ' + l for l in new_json.split('\n'))
    
    new_lines = lines[:start_idx] + [f"            presetTemplates: {indented_json.strip()},\n"] + lines[end_idx:]
    
    with open('static/js/app.js', 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Updated app.js successfully.")
else:
    print(f"Failed. start_idx={start_idx}, end_idx={end_idx}")
