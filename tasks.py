from shutil import copyfile
import os
import sys
import webbrowser

from invoke import task

OSF_GIT_URL = 'https://github.com/CenterForOpenScience/osf.io.git'
POSTGRES_BRANCH = 'feature/django-osf'

@task
def setup_tests(ctx, update=False, requirements=True, branch=POSTGRES_BRANCH):
    if update and os.path.exists('osf.io'):
        ctx.run('rm -rf osf.io/', echo=True)
        print('Cleaned up.')
    first_run = False
    if not os.path.exists('osf.io'):
        first_run = True
        # '--depth 1' excludes the history (for faster cloning)
        ctx.run('git clone --branch={} {} --depth 1'.format(branch, OSF_GIT_URL), echo=True)

    os.chdir('osf.io')
    if update and not first_run:
        print('Updating osf.io ({})'.format(branch))
        ctx.run('git pull origin {}'.format(branch), echo=True)
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
        # Install list-of-licenses package
        ctx.run('npm install list-of-licenses')
        # Install osf requirements
        ctx.run('invoke requirements')
        ctx.run('invoke requirements --addons --dev')
        # Hack to fix package conflict between uritemplate and uritemplate.py (dependency of github3.py)
        ctx.run('pip uninstall uritemplate.py --yes')
        ctx.run('pip install uritemplate.py==0.3.0')
        # Install osf-models test requirements
        ctx.run('pip install -r {}'.format(os.path.join('osf_tests', 'requirements.txt')), echo=True)
    os.chdir('..')
    print('Finished test setup.')

@task
def flake(ctx):
    """Run flake8 on codebase."""
    ctx.run('flake8 .', echo=True)

@task(pre=[flake])
def test(ctx, setup=False, update=False, requirements=True, branch=POSTGRES_BRANCH):
    import pytest
    # Paths relative to osf.io/
    TEST_MODULES = [
        'osf_tests',
        os.path.join('tests', 'test_views.py'),
    ]
    if setup or update:
        setup_tests(ctx, update=update, requirements=requirements, branch=branch)
    if not os.path.exists('osf.io'):
        print('Must run "inv setup_tests" before running tests.')
        sys.exit(1)
    os.chdir('osf.io')
    retcode = pytest.main(TEST_MODULES)
    os.chdir('..')
    sys.exit(retcode)

@task
def readme(ctx, browse=False):
    ctx.run('rst2html.py README.rst > README.html')
    if browse:
        webbrowser.open_new_tab('README.html')
