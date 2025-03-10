import celery
import celery.signals
import celery_worker_healthcheck


celery.signals.worker_init.connect(weak=False)(celery_worker_healthcheck.start)
CELERY = celery.Celery()
