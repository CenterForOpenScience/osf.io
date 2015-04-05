"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""

import os
import sys

from django.core.wsgi import get_wsgi_application


# Ensure root OSF directory is in sys.path
HERE = os.path.dirname(os.path.abspath(__file__))
if HERE not in sys.path:
    sys.path.append(os.path.abspath(os.path.join(HERE, '..', '..')))

# from website.app import init_app

# init_app(set_backends=True)

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "api.api.settings")

application = get_wsgi_application()
