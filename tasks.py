# encoding: utf-8

from invoke import task, run

from waterbutler import settings


@task
def tornado(port=settings.PORT, address=settings.ADDRESS, debug=settings.DEBUG):
    from waterbutler.server import serve
    serve(port, address, debug)


@task
def test():
    cmd = 'py.test --cov-report term-missing --cov waterbutler tests'
    run(cmd, pty=True)
