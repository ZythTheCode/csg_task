import multiprocessing
import os

# Worker configuration
worker_class = 'gthread'
workers = int(os.environ.get('WEB_CONCURRENCY', 4))
threads = 2
timeout = 120
keepalive = 5

# Worker recycling to prevent memory leaks
max_requests = 1000
max_requests_jitter = 50

# Logging
accesslog = '-'
errorlog = '-'
loglevel = 'info'

# Bind
bind = f"0.0.0.0:{os.environ.get('PORT', '8000')}"
