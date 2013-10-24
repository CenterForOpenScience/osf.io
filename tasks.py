#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
from invoke import task, run, ctask

from website import settings
from framework.tasks import celery

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
def mailserver(port=1025):
    '''Run a SMTP test server.'''
    run("python -m smtpd -n -c DebuggingServer localhost:{port}".format(port=port), pty=True)


@task
def requirements():
    '''Install dependencies.'''
    run("pip install --upgrade -r dev-requirements.txt", pty=True)


@ctask(help={
    'module': "Just runs tests/STRING.py.",
})
def test(ctx, module=None):
    """
    Run the test suite.
    """
    # Allow selecting specific submodule
    specific_module = " --tests=tests/%s.py" % module
    args = (specific_module if module else " tests/")
    # Use pty so the process buffers "correctly"
    ctx.run("nosetests" + args, pty=True)
