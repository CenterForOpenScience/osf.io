"""Global variables related to Django requests

Made available in a separate file so as to be importable by Flask code, before (or in the absence of) Django
"""
import threading

api_globals = threading.local()

# Store a reference to the current Django request. Threads may be reused; empty after request.
api_globals.request = None

# Set _celery_tasks to be used in 'framework.tasks.enqueue_task'
api_globals._celery_tasks = None
