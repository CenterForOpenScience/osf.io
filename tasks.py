#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
import os

from invoke import task, run

from website import settings

SOLR_DEV_PATH = os.path.join("scripts", "solr-dev")  # Path to example solr app


@task
def server():
    run("python main.py")


# Shell command adapted from Flask-Script. See NOTICE for license info.
@task
def shell():
    import konch
    config = konch.use_file('.konchrc')
    konch.start(**config)


@task
def mongo(daemon=False):
    '''Run the mongod process.
    '''
    port = settings.DB_PORT
    cmd = "mongod --port {0}".format(port)
    if daemon:
        cmd += " --fork"
    run(cmd)


@task
def mongoshell():
    '''Run the mongo shell for the OSF database.'''
    db = settings.DB_NAME
    port = settings.DB_PORT
    run("mongo {db} --port {port}".format(db=db, port=port), pty=True)


@task
def celery_worker(level="debug"):
    '''Run the Celery process.'''
    run("celery worker -A framework.tasks -l {0}".format(level))


@task
def rabbitmq():
    '''Start a local rabbitmq server.

    NOTE: this is for development only. The production environment should start
    the server as a daemon.
    '''
    run("rabbitmq-server", pty=True)


@task
def solr():
    '''Start a local solr server.

    NOTE: Requires that Java and Solr are installed. See README for more instructions.
    '''
    os.chdir(SOLR_DEV_PATH)
    run("java -jar start.jar", pty=True)

@task
def solr_migrate():
    '''Migrate the solr-enabled models.'''
    run("python -m website.solr_migration.migrate")

@task
def mailserver(port=1025):
    '''Run a SMTP test server.'''
    run("python -m smtpd -n -c DebuggingServer localhost:{port}".format(port=port), pty=True)


@task
def requirements(all=False, addons=False):
    '''Install dependencies.'''
    if all:
        run("pip install --upgrade -r dev-requirements.txt", pty=True)
        addon_requirements()
    elif addons:
        addon_requirements()
    else:
        run("pip install --upgrade -r dev-requirements.txt", pty=True)


@task
def test_module(module=None):
    """
    Helper for running tests.
    """
    test_cmd = 'nosetests'
    # Allow selecting specific submodule
    args = " -s %s" % module
    # Use pty so the process buffers "correctly"
    run(test_cmd + args, pty=True)


@task
def test_osf():
    """Run the OSF test suite."""
    test_module(module="tests/")


@task
def test_addons():
    """Run all the tests in the addons directory.
    """
    test_module(module="website/addons/")


@task
def test():
    """Alias of `invoke test_osf`.
    """
    test_osf()


@task
def test_all():
    test_osf()
    test_addons()


# TODO: user bower once hgrid is released
@task
def get_hgrid():
    """Get the latest development version of hgrid and put it in the static
    directory.
    """
    target = 'website/static/vendor/hgrid'
    run('git clone https://github.com/CenterForOpenScience/hgrid.git')
    print('Removing old version')
    run('rm -rf {0}'.format(target))
    print('Replacing with fresh version')
    run('mkdir {0}'.format(target))
    run('mv hgrid/dist/hgrid.js {0}'.format(target))
    run('mv hgrid/dist/hgrid.css {0}'.format(target))
    run('mv hgrid/dist/images {0}'.format(target))
    run('rm -rf hgrid/')
    print('Finished')


@task
def addon_requirements(mfr=1):
    """Install all addon requirements."""
    addon_root = 'website/addons'
    for directory in os.listdir(addon_root):
        path = os.path.join(addon_root, directory)
        if os.path.isdir(path):
            try:
                open(os.path.join(path, 'requirements.txt'))
                print 'Installing requirements for {0}'.format(directory)
                run('pip install --upgrade -r {0}/{1}/requirements.txt'.format(addon_root, directory), pty=True)
            except IOError:
                pass
    if mfr:
        mfr_requirements()
    print('Finished')


@task
def mfr_requirements():
    """Install modular file renderer requirements"""
    mfr = 'mfr'
    print 'Installing mfr requirements'
    run('pip install --upgrade -r {0}/requirements.txt'.format(mfr), pty=True)
