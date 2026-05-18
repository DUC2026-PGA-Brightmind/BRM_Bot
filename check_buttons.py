import re

with open('admin_bot.py', encoding='utf-8-sig') as f:
    content = f.read()

kb_texts = re.findall(r'KeyboardButton\("([^"]+)"\)', content)
handler_texts = re.findall(r'm\.text == "([^"]+)"', content)
in_blocks = re.findall(r'm\.text in \[([^\]]+)\]', content)

# Build flat set of all handled texts
handled = set(handler_texts)
for block in in_blocks:
    items = re.findall(r'"([^"]+)"', block)
    handled.update(items)

print("=== ALL UNHANDLED BUTTONS ===")
missing = []
for b in kb_texts:
    if b not in handled:
        missing.append(b)
        print(f"  MISSING HANDLER: {repr(b)}")

if not missing:
    print("  All buttons have handlers!")

print(f"\nTotal buttons: {len(kb_texts)}")
print(f"Total handlers: {len(handled)}")
