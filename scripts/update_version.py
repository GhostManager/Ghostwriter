import sys
import re

version = sys.argv[1].lstrip('v')
release_date = sys.argv[2]

# Update VERSION file
with open('VERSION', 'w', encoding='utf-8') as f:
    f.write(f"v{version}\n{release_date}\n")

# Update base.py
path = 'config/settings/base.py'
with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

content = re.sub(r'^__version__\s*=\s*["\'].*?["\']', f'__version__ = "{version}"', content, flags=re.MULTILINE)
content = re.sub(r'^RELEASE_DATE\s*=\s*["\'].*?["\']', f'RELEASE_DATE = "{release_date}"', content, flags=re.MULTILINE)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)
