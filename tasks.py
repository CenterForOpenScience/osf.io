#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
from invoke import task, run, ctask

from website import settings
from framework.celery.celery import celery

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

# FIXME
@task
def celery():
    '''Run the Celery process.'''
    celery.start()


@task
def requirements():
    '''Install dependencies.'''
    run("pip install --upgrade -r dev-requirements.txt")


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
