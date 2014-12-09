# encoding: utf-8

from invoke import task

from waterbutler.server import settings


@task
def tornado(port=settings.PORT, address=settings.ADDRESS, debug=settings.DEBUG):
    from waterbutler.server import serve
    serve(port, address, debug)
