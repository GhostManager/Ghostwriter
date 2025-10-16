import sys
import re

version = sys.argv[1].lstrip('v')
release_date = sys.argv[2]

# Update VERSION file
with open('VERSION', 'w') as f:
    f.write(f"v{version}\n{release_date}\n")

# Update base.py
path = '/config/settings/base.py'
with open(path, 'r') as f:
    content = f.read()

content = re.sub(r'__version__\s*=\s*["\'].*?["\']', f'__version__ = "{version}"', content)
content = re.sub(r'RELEASE_DATE\s*=\s*["\'].*?["\']', f'RELEASE_DATE = "{release_date}"', content)

with open(path, 'w') as f:
    f.write(content)
