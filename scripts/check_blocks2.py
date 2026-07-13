import os
import json

ingestion_id = 'd96e666b-7d27-4ed0-9a73-81c96d5e1bb5'
base_dir = rf'c:\Users\Anurag shukla\mocktest\storage\mineru_outputs\{ingestion_id}\{ingestion_id}'
images_dir = os.path.join(base_dir, 'images')

q54_img = '0f39ccf84195c26dfbb601e504cef01ebd774c5fe9d04fba9bb0da060c3a3112.jpg'
q62_img = 'dae219bf9f1fa98d503805ba061347c97a7d73878633f7c2b999caae4f8e2469.jpg'

print(f'Q54 image exists: {os.path.exists(os.path.join(images_dir, q54_img))}')
print(f'Q62 image exists: {os.path.exists(os.path.join(images_dir, q62_img))}')

cl_path = os.path.join(base_dir, f'{ingestion_id}_content_list.json')
with open(cl_path, 'r', encoding='utf-8') as f:
    blocks = json.load(f)

# Find Q54 blocks
for i, b in enumerate(blocks):
    if b.get('type') == 'text' and '54. Consider' in b.get('text', ''):
        print('\n--- Blocks near Q54 ---')
        for j in range(max(0, i-2), min(len(blocks), i+10)):
            text = (blocks[j].get('text') or blocks[j].get('img_path') or '').replace('\n', ' ')
            print(f'Block {j} [{blocks[j].get("type")}]: {text[:60]}')
        break

# Find Q62 blocks
for i, b in enumerate(blocks):
    if b.get('type') == 'text' and '62. Match List-I' in b.get('text', ''):
        print('\n--- Blocks near Q62 ---')
        for j in range(max(0, i-2), min(len(blocks), i+10)):
            text = (blocks[j].get('text') or blocks[j].get('img_path') or '').replace('\n', ' ')
            print(f'Block {j} [{blocks[j].get("type")}]: {text[:60]}')
        break
