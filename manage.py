#!/usr/bin/env python
import sys
import os


if __name__ == "__main__":
    os.environ.setdefault("DJANGO_SETTINGS_MODULE", "admin.base.settings")

    from django.core.management import execute_from_command_line
    from website.app import init_app

    init_app(set_backends=True, routes=False, attach_request_handlers=False)

    if 'livereload' in sys.argv:
        from django.core.wsgi import get_wsgi_application
        from livereload import Server
        import django.conf as conf
        conf.settings.STATIC_URL = '/static/'
        application = get_wsgi_application()
        server = Server(application)
        server.watch('admin/')

        server.serve(port=8001)
    else:
        execute_from_command_line(sys.argv)
