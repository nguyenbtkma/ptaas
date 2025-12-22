"""
Celery application configuration for PTaaS
"""
from celery import Celery
from kombu import Queue
import os
from dotenv import load_dotenv

load_dotenv(dotenv_path=os.path.join(os.path.dirname(__file__), '..', '..', '.env'))

# Initialize Celery
celery_app = Celery(
    'ptaas',
    broker=os.getenv('CELERY_BROKER_URL', 'redis://redis:6379/0'),
    backend=os.getenv('CELERY_RESULT_BACKEND', 'redis://redis:6379/0'),
    include=['app.tasks']
)

# Use a dedicated queue but also accept default celery queue to avoid stale messages
celery_app.conf.task_default_queue = 'ptaas'
celery_app.conf.task_queues = (
    Queue('ptaas', routing_key='ptaas'),
    Queue('celery', routing_key='celery'),  # Accept default queue too
)
celery_app.conf.task_default_exchange = 'ptaas'
celery_app.conf.task_default_routing_key = 'ptaas'

# Celery Configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json', 'application/json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=3600,  # 1 hour max per task
    task_soft_time_limit=3300,  # Soft limit at 55 minutes
    worker_prefetch_multiplier=1,
    worker_max_tasks_per_child=50,
    result_accept_content=['json', 'application/json'],
    worker_enable_remote_control=False,  # Avoid pickle-based pidbox/mingle messages
    broker_connection_retry_on_startup=True,
)

if __name__ == '__main__':
    celery_app.start()
