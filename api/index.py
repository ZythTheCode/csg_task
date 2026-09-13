import os
import sys

# Ensure Django project root is on Python sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from csg_project.wsgi import application

# Vercel serverless function entrypoint
app = application
