# encoding: utf-8

from invoke import task

from server import settings


@task
def tornado(port=settings.PORT, address=settings.ADDRESS, debug=settings.DEBUG):
    from server import main
    main.main(port, address, debug)
