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
def requirements():
    '''Install dependencies.'''
    run("pip install --upgrade -r dev-requirements.txt", pty=True)
    addon_requirements()


@task
def test_module(module=None, coverage=False, browse=False):
    """
    Helper for running tests.
    """
    # Allow selecting specific submodule
    args = " --tests=%s" % module
    if coverage:
        args += " --with-coverage --cover-html"
    # Use pty so the process buffers "correctly"
    run("nosetests" + args, pty=True)
    if coverage and browse:
        run("open cover/index.html")


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
def addon_requirements():
    """Install all addon requirements."""
    addon_root = 'website/addons'
    for addon in [directory for directory in os.listdir(addon_root) if os.path.isdir(os.path.join(addon_root, directory))]:
        try:
            open('{0}/{1}/requirements.txt'.format(addon_root, addon)).close()
            print 'Installing requirements for {0}'.format(addon)
            run('pip install --upgrade -r {0}/{1}/requirements.txt'.format(addon_root, addon), pty=True)
        except IOError:
            pass
    mfr_requirements()
    print('Finished')


@task
def mfr_requirements():
    """Install modular file renderer requirements"""
    mfr = 'mfr'
    print 'Installing mfr requirements'
    run('pip install --upgrade -r {0}/requirements.txt'.format(mfr), pty=True)
