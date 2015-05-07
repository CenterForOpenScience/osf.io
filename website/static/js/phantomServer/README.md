1. In website/settings/local.py make USE_CELERY  True
2. Run 'invoke phantom' to start phantom on Express Server.
3. Run 'invoke rabbitmq' & 'invoke celery_worker' for runing celery asynchronous tasks.
