import os
from celery import Celery

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "imara_project.settings")

app = Celery("imara")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()