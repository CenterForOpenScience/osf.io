import sys

from invoke import task, run


@task
def install(upgrade=False, pip_cache=None, wheel_repo=None):
    cmd = 'pip install -r dev-requirements.txt'

    if upgrade:
        cmd += ' --upgrade'
    if pip_cache:
        cmd += ' --download-cache={}'.format(pip_cache)

    if wheel_repo:
        run('pip install wheel', pty=False)
        # current python version, expected git branch name
        ver = '.'.join([str(i) for i in sys.version_info[0:2]])
        folder = 'wheelhouse-{}'.format(ver)
        name = 'wheelhouse-{}.zip'.format(ver)
        url = '{}/archive/{}.zip'.format(wheel_repo, ver)
        # download and extract the wheelhouse github repository archive
        run('curl -o {} -L {}'.format(name, url), pty=False)
        run('unzip {}'.format(name), pty=False)
        # run pip install w/ the wheelhouse folder specified
        run('{} --use-wheel --find-links={}'.format(cmd, folder), pty=False)
        # cleanup wheelhouse folder and archive file
        run('rm -rf {}'.format(folder), pty=False)
        run('rm -f {}'.format(name), pty=False)
    else:
        run(cmd, pty=False)


@task
def flake():
    run('flake8 .')


@task
def test(verbose=False):
    cmd = 'py.test --cov-report term-missing --cov waterbutler tests'
    if verbose:
        cmd += ' -v'
    run(cmd, pty=False)


@task
def celery():
    from waterbutler.providers.osfstorage.tasks import app
    app.worker_main(['worker'])
