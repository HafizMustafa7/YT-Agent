import json

file_path = r'C:\Users\khizr\.gemini\antigravity\brain\5d6262f4-d100-4ccc-92ee-376342ab6ccc\.system_generated\steps\33\output.txt'

with open(file_path, 'r', encoding='utf-8') as f:
    data = json.load(f)

targets = [
    'YOUTOMIZE - Trend Analysis (Workspace Refined)',
    'YOUTOMIZE - Settings (Refined)',
    'YOUTOMIZE - Pricing Plans',
    'YOUTOMIZE - Checkout',
    'YOUTOMIZE - Final Video Upload',
    'Video Generation Storyboard',
    'YouTube AI Video Automation Flow'
]

with open('extract_output.txt', 'w', encoding='utf-8') as out:
    for screen in data.get('screens', []):
        if screen.get('title') in targets:
            title = screen.get('title')
            url = screen.get('htmlCode', {}).get('downloadUrl', 'No URL found')
            out.write(f"Title: {title}\nDownload URL: {url}\n\n")
