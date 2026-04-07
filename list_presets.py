import json
import re

with open('static/js/app.js', 'r', encoding='utf-8') as f:
    content = f.read()

start = content.find('presetTemplates: [')
if start != -1:
    print("Found presetTemplates")
    for match in re.finditer(r'\{\s*\"label\":\s*\"([^\"]+)\",\s*\"value\":\s*\"([^\"]+)\"', content[start:start+100000]):
        print(match.group(1), "->", match.group(2))
