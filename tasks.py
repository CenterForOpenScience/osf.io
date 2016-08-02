from shutil import copyfile
import os
import sys
import webbrowser

from invoke import task

OSF_GIT_URL = 'https://github.com/sloria/osf.io.git'
POSTGRES_BRANCH = 'feature/postgres'

@task
def setup_tests(ctx, update=False, requirements=True):
    first_run = False
    if not os.path.exists('osf.io'):
        first_run = True
        # '--depth 1' excludes the history (for faster cloning)
        ctx.run('git clone --branch={} {} --depth 1'.format(POSTGRES_BRANCH, OSF_GIT_URL), echo=True)

    os.chdir('osf.io')
    if update and not first_run:
        print('Updating osf.io ({})'.format(POSTGRES_BRANCH))
        ctx.run('git pull origin {}'.format(POSTGRES_BRANCH), echo=True)
    # Copy necessary local.py files
    try:
        copyfile(
            os.path.join('website', 'settings', 'local-travis.py'),
            os.path.join('website', 'settings', 'local.py')
        )
    except IOError:
        pass
    try:
        copyfile(
            os.path.join('api', 'settings', 'local-dist.py'),
            os.path.join('api', 'settings', 'local.py')
        )
    except IOError:
        pass
    if requirements:
        # Install osf requirements
        ctx.run('pip install -r {}'.format(os.path.join('requirements.txt')), echo=True)
        # Install osf-models test requirements
        ctx.run('pip install -r {}'.format(os.path.join('osf_models_tests', 'requirements.txt')), echo=True)
    os.chdir('..')
    print('Finished test setup.')


@task
def test(ctx, setup=False):
    import pytest
    if setup:
        setup_tests(ctx)
    if not os.path.exists('osf.io'):
        print('Must run "inv setup_tests" before running tests.')
        sys.exit(1)
    os.chdir('osf.io')
    retcode = pytest.main(['osf_models_tests'])
    os.chdir('..')
    sys.exit(retcode)


@task
def flake(ctx):
    """Run flake8 on codebase."""
    ctx.run('flake8 .', echo=True)

@task
def readme(ctx, browse=False):
    ctx.run("rst2html.py README.rst > README.html")
    if browse:
        webbrowser.open_new_tab('README.html')
