#!/usr/bin/env python
import os
import sys
from website.app import init_app


if __name__ == "__main__":
    os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'api.base.settings')

    from django.core.management import execute_from_command_line

    init_app(set_backends=True, routes=False, mfr=False, attach_request_handlers=False)

    execute_from_command_line(sys.argv)
