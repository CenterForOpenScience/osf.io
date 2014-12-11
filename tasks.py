from invoke import task, run

from waterbutler import settings


@task
def install(upgrade=False):
    cmd = 'pip install -r dev-requirements.txt'
    if upgrade:
        cmd += ' --upgrade'
    run(cmd)


@task
def flake():
    run('flake8 .')


@task
def test():
    cmd = 'py.test --cov-report term-missing --cov waterbutler tests'
    run(cmd, pty=True)


@task
def tornado(port=settings.PORT, address=settings.ADDRESS, debug=settings.DEBUG):
    from waterbutler.server import serve
    serve(port, address, debug)
