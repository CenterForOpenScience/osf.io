# -*- coding: utf-8 -*-

import os
import sys

from invoke import task, run

from waterbutler import settings


@task
def install(upgrade=False, pip_cache=None, wheel_repo=None):
    cmd = 'pip install -r dev-requirements.txt'

    if upgrade:
        cmd += ' --upgrade'
    if pip_cache:
        cmd += ' --download-cache={}'.format(pip_cache)

    if wheel_repo:
        run('pip install wheel', pty=True)
        # get the current python version, expected git branch name
        ver = '.'.join([str(i) for i in sys.version_info[0:2]])
        name = 'wheelhouse-{}'.format(ver)
        ext = '.zip'
        url = '{}/archive/{}{}'.format(wheel_repo, ver, ext)
        # download and extract the wheelhouse github repository archive
        run('curl -o {}{} -L {}'.format(name, ext, url), pty=True)
        run('unzip {}{}'.format(name, ext, name), pty=True)
        # run pip install w/ the wheelhouse dependencies available
        run(cmd + ' --use-wheel --find-links={}'.format(name), pty=True)
        # cleanup wheelhouse-{ver} folder and wheelhouse-{ver}{ext} file
        run('rm -rf {}'.format(name), pty=True)
        run('rm -f {}{}'.format(name, ext), pty=True)
    else:
        run(cmd, pty=True)


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
