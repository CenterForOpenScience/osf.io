"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
from django.core.wsgi import get_wsgi_application
from website.app import init_app

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin.base.settings')

init_app(set_backends=True, routes=False, attach_request_handlers=False)

application = get_wsgi_application()
