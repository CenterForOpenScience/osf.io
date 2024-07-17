"""
WSGI config for api project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/1.8/howto/deployment/wsgi/
"""
from website import settings

if settings.NEWRELIC_INI_PATH:
    try:
        import newrelic.agent
        newrelic.agent.initialize(settings.NEWRELIC_INI_PATH)
    except Exception as err:
        raise Exception(f'Unable to initialize newrelic! {err}')

import os  # noqa
from django.core.wsgi import get_wsgi_application  # noqa
from website.app import init_app  # noqa

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'admin.base.settings')

init_app(set_backends=True, routes=False, attach_request_handlers=False)

application = get_wsgi_application()
