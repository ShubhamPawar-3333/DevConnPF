"""
Celery application configuration for the devconnpf project.

This module sets up Celery with Django settings and auto-discovers
tasks from all installed apps.
"""

import os

from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'devconnpf.settings')

app = Celery('devconnpf')

# Load task modules from all registered Django apps.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Auto-discover tasks in all installed apps (looks for tasks.py in each app).
app.autodiscover_tasks()


@app.task(bind=True, ignore_result=True)
def debug_task(self):
    """A debug task that prints its own request info."""
    print(f'Request: {self.request!r}')
