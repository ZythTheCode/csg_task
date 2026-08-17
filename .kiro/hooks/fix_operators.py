"""Fix == and != operators without spaces inside Django template tags, and collapse multi-line {{ }} tags."""
import re
import sys

path = sys.argv[1] if len(sys.argv) > 1 else r'd:\CSG\templates\tasks\list.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

def fix_tag(match):
    tag = match.group(0)
    # Add space around == that's missing spaces
    tag = re.sub(r'(\w)==(\w)', r'\1 == \2', tag)
    tag = re.sub(r"(\w)==(')", r"\1 == \2", tag)
    # Add space around != that's missing spaces
    tag = re.sub(r"(\w)!=(\w)", r"\1 != \2", tag)
    tag = re.sub(r"(\w)!='", r"\1 != '", tag)
    # Fix >= without space
    tag = re.sub(r'(\w)>=\s', r'\1 >= ', tag)
    tag = re.sub(r'">= ', r'" >= ', tag)
    return tag

# Fix operators inside {% %} tags
content = re.sub(r'\{%.*?%\}', fix_tag, content)

# Fix multi-line {{ }} variable tags - collapse to single line
def collapse_var_tag(match):
    tag = match.group(0)
    # Replace newlines and surrounding whitespace with a single space
    collapsed = re.sub(r'\s*\n\s*', ' ', tag)
    # Normalize internal whitespace
    collapsed = re.sub(r'\{\{\s+', '{{ ', collapsed)
    collapsed = re.sub(r'\s+\}\}', ' }}', collapsed)
    return collapsed

content = re.sub(r'\{\{[^}]*\n[^}]*\}\}', collapse_var_tag, content)

with open(path, 'w', encoding='utf-8', newline='\n') as f:
    f.write(content)
print(f'Fixed operators and multi-line tags in {path}')
