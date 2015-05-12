1. In website/settings/local.py turn USE_CELERY to True
2. Run 'invoke phantom' to start phantom app using Express Server.
3. Run 'invoke rabbitmq' & 'invoke celery_worker' for runing celery asynchronous tasks.
