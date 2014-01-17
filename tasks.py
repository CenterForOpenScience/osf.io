#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
import os
from invoke import task, run, ctask

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
    run("celery worker -A framework -l {0}".format(level))


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
