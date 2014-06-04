#!/usr/bin/env python
# -*- coding: utf-8 -*-
'''Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
'''
import os
import sys
import code

from invoke import task, run

from website import settings

SOLR_DEV_PATH = os.path.join("scripts", "solr-dev")  # Path to example solr app


@task
def server():
    run("python main.py")


SHELL_BANNER = """
{version}

Welcome to the OSF Python Shell. Happy hacking!

Available variables:

{context}
"""


def make_shell_context():
    from framework import Q
    from framework.auth.model import User
    from framework import db
    from website.app import init_app
    from website.project.model import Node
    from website import models  # all models
    import requests
    app = init_app()
    context = {'app': app,
                'db': db,
                'User': User,
                'Node': Node,
                'Q': Q,
                'models': models,
                'run_tests': test,
                'rget': requests.get,
                'rpost': requests.post,
                'rdelete': requests.delete,
                'rput': requests.put
    }
    try:  # Add a fake factory for generating fake names, emails, etc.
        from faker import Factory
        fake = Factory.create()
        context['fake'] = fake
    except ImportError:
        pass
    return context


def format_context(context):
    lines = []
    for name, obj in context.items():
        line = "{name}: {obj!r}".format(**locals())
        lines.append(line)
    return '\n'.join(lines)

# Shell command adapted from Flask-Script. See NOTICE for license info.
@task
def shell():
    context = make_shell_context()
    banner = SHELL_BANNER.format(version=sys.version,
        context=format_context(context)
    )
    try:
        try:
            # 0.10.x
            from IPython.Shell import IPShellEmbed
            ipshell = IPShellEmbed(banner=banner)
            ipshell(global_ns={}, local_ns=context)
        except ImportError:
            # 0.12+
            from IPython import embed
            embed(banner1=banner, user_ns=context)
        return
    except ImportError:
        pass
    # fallback to basic python shell
    code.interact(banner, local=context)
    return

@task
def mongo(daemon=False,
          logpath="/usr/local/var/log/mongodb/mongo.log"):
    """Run the mongod process.
    """
    port = settings.DB_PORT
    cmd = "mongod --port {0} --logpath {1}".format(port, logpath)
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
def test_module(module=None, verbosity=2):
    """
    Helper for running tests.
    """
    test_cmd = 'nosetests'
    # Allow selecting specific submodule
    module_fmt = ' '.join(module) if isinstance(module, list) else module
    args = " --verbosity={0} -s {1}".format(verbosity, module_fmt)
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
    modules = []
    for addon in settings.ADDONS_REQUESTED:
        module = os.path.join(settings.BASE_PATH, 'addons', addon)
        modules.append(module)
    test_module(module=modules)


@task
def test():
    """Alias of `invoke test_osf`.
    """
    test_osf()


@task
def test_all():
    test_osf()
    test_addons()

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
