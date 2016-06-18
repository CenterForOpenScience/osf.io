#!/usr/bin/env python
import sys

if __name__ == '__main__':

    from django.core.management import execute_from_command_line
    from website.app import init_app

    init_app(set_backends=True, routes=False, attach_request_handlers=False)

    execute_from_command_line(sys.argv)
