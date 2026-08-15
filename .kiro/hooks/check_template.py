"""Hook script to validate Django template syntax."""
import os
import sys
import warnings

# Suppress dependency warnings that can cause noise
warnings.filterwarnings("ignore")

# Ensure the project root is on the path
project_root = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
sys.path.insert(0, project_root)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "csg_project.settings")

import django
django.setup()

from django.template.loader import get_template
from django.template import TemplateSyntaxError

if len(sys.argv) < 2:
    print("No file argument provided")
    sys.exit(1)

# Normalize the path (handles both forward and backslashes)
filepath = os.path.normpath(sys.argv[1])

# Extract the template-relative path
templates_dir = os.path.sep + "templates" + os.path.sep
if templates_dir in filepath:
    template_name = filepath.split(templates_dir)[-1].replace(os.path.sep, "/")
elif filepath.startswith("templates" + os.path.sep):
    template_name = filepath[len("templates" + os.path.sep):].replace(os.path.sep, "/")
else:
    print(f"File not in templates directory: {filepath}")
    sys.exit(0)

try:
    get_template(template_name)
    print(f"Template OK: {template_name}")
except TemplateSyntaxError as e:
    print(f"Template syntax error in {template_name}: {e}")
    sys.exit(1)
except Exception as e:
    print(f"Error loading template {template_name}: {e}")
    sys.exit(1)
