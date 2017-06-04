#!/usr/bin/env python
import sys

if __name__ == '__main__':
    from django.core.management import execute_from_command_line

    # allow the osf app/model initialization to be skipped so we can run django
    # commands like collectstatic w/o requiring a database to be running
    if '--no-init-app' in sys.argv:
        sys.argv.remove('--no-init-app')
    else:
        from website.app import init_app
        init_app(set_backends=True, routes=False, attach_request_handlers=False)

    execute_from_command_line(sys.argv)
