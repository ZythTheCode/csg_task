"""
Fix Django template syntax issues that break on Python 3.13 / strict Django template parsing:
1. Multi-line {{ variable }} tags (must be single-line)
2. == without spaces in {% if %} tags
3. >= without spaces in {% if %} tags

Run: python fix_templates.py
"""
import re
import sys
import os

TEMPLATE_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'templates')

def fix_template(filepath):
    content = open(filepath, encoding='utf-8').read()
    original = content

    # 1. Fix multi-line {{ }} variable tags
    def fix_var(m):
        inner = m.group(0)[2:-2]
        inner = re.sub(r'\s+', ' ', inner).strip()
        return '{{ ' + inner + ' }}'
    content = re.sub(r'\{\{[^}]*?\n[^}]*?\}\}', fix_var, content)

    # 2. Fix == without spaces in single-line {% %} tags
    def fix_tag(m):
        tag = m.group(0)
        if '===' in tag:
            return tag
        return re.sub(r'(?<!=)==(?!=)', ' == ', tag)
    content = re.sub(r'\{%[^\n%]+%\}', fix_tag, content)
    content = content.replace('  ==  ', ' == ')

    # 3. Fix >= without spaces
    content = re.sub(r'(\w|")\>=\s', lambda m: m.group(0)[0] + ' >= ', content)

    if content != original:
        open(filepath, 'w', encoding='utf-8').write(content)
        return True
    return False

def main():
    fixed_count = 0
    target = sys.argv[1] if len(sys.argv) > 1 else TEMPLATE_DIR

    if os.path.isfile(target):
        if fix_template(target):
            print(f'  Fixed: {target}')
            fixed_count += 1
    else:
        for root, dirs, files in os.walk(target):
            for f in files:
                if f.endswith('.html'):
                    path = os.path.join(root, f)
                    if fix_template(path):
                        print(f'  Fixed: {os.path.relpath(path, TEMPLATE_DIR)}')
                        fixed_count += 1

    if fixed_count:
        print(f'\nFixed {fixed_count} template(s).')
    else:
        print('All templates OK.')

if __name__ == '__main__':
    main()
