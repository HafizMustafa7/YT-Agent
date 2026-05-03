import sys

file_path = r'c:\Users\omerf\Desktop\Project\FYP\YT-Agent\backend\app\services\video_service.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

# We want to remove the block that starts with "# 1. Start Veo job (generate or extend)"
# which was accidentally duplicated and is now around line 968.
# But I need to be careful not to remove the catch/finally of the try block.

start_line = -1
end_line = -1

for i, line in enumerate(lines):
    if i > 900 and "# 1. Start Veo job (generate or extend)" in line:
        start_line = i
        break

if start_line != -1:
    # Look for the last line of the duplicated block
    # logger.info("Frame %d completed (asset=%s, url=%s, r2_path=%s)", frame_num, asset_id, public_url or "N/A", r2_path)
    for i in range(start_line, len(lines)):
        if 'logger.info("Frame %d completed (asset=%s, url=%s, r2_path=%s)"' in lines[i]:
            end_line = i
            break

if start_line != -1 and end_line != -1:
    print(f"Removing lines {start_line+1} to {end_line+1}")
    new_lines = lines[:start_line] + lines[end_line+1:]
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print("Successfully cleaned up the file.")
else:
    print(f"Could not find the block to remove. start_line={start_line}, end_line={end_line}")
