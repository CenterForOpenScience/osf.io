#!/usr/bin/env python
import logging
import sys
import os

if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    # allow the osf app/model initialization to be skipped so we can run django
    # commands like collectstatic w/o requiring a database to be running
    if '--no-init-app' in sys.argv:
        sys.argv.remove('--no-init-app')
        logging.basicConfig(level=logging.INFO)
    else:
        from website.app import init_app
        init_app(set_backends=True, routes=False, attach_request_handlers=False, fixtures=False)

    if os.environ.get('DJANGO_SETTINGS_MODULE') == 'admin.base.settings' and 'migrate' in sys.argv:
        raise RuntimeError('Running migrations from the admin project is disallowed.')

    execute_from_command_line(sys.argv)
