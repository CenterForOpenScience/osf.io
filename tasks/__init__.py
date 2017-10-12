#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""Invoke tasks. To run a task, run ``$ invoke <COMMAND>``. To see a list of
commands, run ``$ invoke --list``.
"""
import os
import sys
import json
import platform
import subprocess
import logging
from time import sleep

import invoke
from invoke import Collection

from website import settings
from .utils import pip_install, bin_prefix

logging.getLogger('invoke').setLevel(logging.CRITICAL)

# gets the root path for all the scripts that rely on it
HERE = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), '..'))
WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')
CONSTRAINTS_PATH = os.path.join(HERE, 'requirements', 'constraints.txt')

ns = Collection()

try:
    from admin import tasks as admin_tasks
    ns.add_collection(Collection.from_module(admin_tasks), name='admin')
except ImportError:
    pass


def task(*args, **kwargs):
    """Behaves the same way as invoke.task. Adds the task
    to the root namespace.
    """
    if len(args) == 1 and callable(args[0]):
        new_task = invoke.task(args[0])
        ns.add_task(new_task)
        return new_task
    def decorator(f):
        new_task = invoke.task(f, *args, **kwargs)
        ns.add_task(new_task)
        return new_task
    return decorator


@task
def server(ctx, host=None, port=5000, debug=True, gitlogs=False):
    """Run the app server."""
    if os.environ.get('WERKZEUG_RUN_MAIN') == 'true' or not debug:
        if os.environ.get('WEB_REMOTE_DEBUG', None):
            import pydevd
            # e.g. '127.0.0.1:5678'
            remote_parts = os.environ.get('WEB_REMOTE_DEBUG').split(':')
            pydevd.settrace(remote_parts[0], port=int(remote_parts[1]), suspend=False, stdoutToServer=True, stderrToServer=True)

        if gitlogs:
            git_logs(ctx)
        from website.app import init_app
        os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
        app = init_app(set_backends=True, routes=True)
        settings.API_SERVER_PORT = port
    else:
        from framework.flask import app

    context = None
    if settings.SECURE_MODE:
        context = (settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
    app.run(host=host, port=port, debug=debug, threaded=debug, extra_files=[settings.ASSET_HASH_PATH], ssl_context=context)


@task
def git_logs(ctx, branch=None):
    from scripts.meta import gatherer
    gatherer.main(branch=branch)


@task
def apiserver(ctx, port=8000, wait=True, autoreload=True, host='127.0.0.1', pty=True):
    """Run the API server."""
    env = os.environ.copy()
    cmd = 'DJANGO_SETTINGS_MODULE=api.base.settings {} manage.py runserver {}:{} --nothreading'\
        .format(sys.executable, host, port)
    if not autoreload:
        cmd += ' --noreload'
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)

    if wait:
        return ctx.run(cmd, echo=True, pty=pty)
    from subprocess import Popen

    return Popen(cmd, shell=True, env=env)


@task
def adminserver(ctx, port=8001, host='127.0.0.1', pty=True):
    """Run the Admin server."""
    env = 'DJANGO_SETTINGS_MODULE="admin.base.settings"'
    cmd = '{} python manage.py runserver {}:{} --nothreading'.format(env, host, port)
    if settings.SECURE_MODE:
        cmd = cmd.replace('runserver', 'runsslserver')
        cmd += ' --certificate {} --key {}'.format(settings.OSF_SERVER_CERT, settings.OSF_SERVER_KEY)
    ctx.run(cmd, echo=True, pty=pty)

@task
def shell(ctx, transaction=True, print_sql=False, notebook=False):
    cmd = 'DJANGO_SETTINGS_MODULE="api.base.settings" python manage.py osf_shell'
    if print_sql:
        cmd += ' --print-sql'
    if notebook:
        cmd += ' --notebook'
    if not transaction:
        cmd += ' --no-transaction'
    return ctx.run(cmd, pty=True, echo=True)

@task(aliases=['mongo'])
def mongoserver(ctx, daemon=False, config=None):
    """Run the mongod process.
    """
    if not config:
        platform_configs = {
            'darwin': '/usr/local/etc/tokumx.conf',  # default for homebrew install
            'linux': '/etc/tokumx.conf',
        }
        platform = str(sys.platform).lower()
        config = platform_configs.get(platform)
    port = settings.DB_PORT
    cmd = 'mongod --port {0}'.format(port)
    if config:
        cmd += ' --config {0}'.format(config)
    if daemon:
        cmd += ' --fork'
    ctx.run(cmd, echo=True)


@task(aliases=['mongoshell'])
def mongoclient(ctx):
    """Run the mongo shell for the OSF database."""
    db = settings.DB_NAME
    port = settings.DB_PORT
    ctx.run('mongo {db} --port {port}'.format(db=db, port=port), pty=True)


@task
def mongodump(ctx, path):
    """Back up the contents of the running OSF database"""
    db = settings.DB_NAME
    port = settings.DB_PORT

    cmd = 'mongodump --db {db} --port {port} --out {path}'.format(
        db=db,
        port=port,
        path=path,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    ctx.run(cmd, echo=True)

    print()
    print('To restore from the dumped database, run `invoke mongorestore {0}`'.format(
        os.path.join(path, settings.DB_NAME)))


@task
def mongorestore(ctx, path, drop=False):
    """Restores the running OSF database with the contents of the database at
    the location given its argument.

    By default, the contents of the specified database are added to
    the existing database. The `--drop` option will cause the existing database
    to be dropped.

    A caveat: if you `invoke mongodump {path}`, you must restore with
    `invoke mongorestore {path}/{settings.DB_NAME}, as that's where the
    database dump will be stored.
    """
    db = settings.DB_NAME
    port = settings.DB_PORT

    cmd = 'mongorestore --db {db} --port {port}'.format(
        db=db,
        port=port,
        pty=True)

    if settings.DB_USER:
        cmd += ' --username {0}'.format(settings.DB_USER)
    if settings.DB_PASS:
        cmd += ' --password {0}'.format(settings.DB_PASS)

    if drop:
        cmd += ' --drop'

    cmd += ' ' + path
    ctx.run(cmd, echo=True)


@task
def sharejs(ctx, host=None, port=None, db_url=None, cors_allow_origin=None):
    """Start a local ShareJS server."""
    if host:
        os.environ['SHAREJS_SERVER_HOST'] = host
    if port:
        os.environ['SHAREJS_SERVER_PORT'] = port
    if db_url:
        os.environ['SHAREJS_DB_URL'] = db_url
    if cors_allow_origin:
        os.environ['SHAREJS_CORS_ALLOW_ORIGIN'] = cors_allow_origin

    if settings.SENTRY_DSN:
        os.environ['SHAREJS_SENTRY_DSN'] = settings.SENTRY_DSN

    share_server = os.path.join(settings.ADDON_PATH, 'wiki', 'shareServer.js')
    ctx.run('node {0}'.format(share_server))


@task(aliases=['celery'])
def celery_worker(ctx, level='debug', hostname=None, beat=False, queues=None, concurrency=None, max_tasks_per_child=None):
    """Run the Celery process."""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    cmd = 'celery worker -A framework.celery_tasks -Ofair -l {0}'.format(level)
    if hostname:
        cmd = cmd + ' --hostname={}'.format(hostname)
    # beat sets up a cron like scheduler, refer to website/settings
    if beat:
        cmd = cmd + ' --beat'
    if queues:
        cmd = cmd + ' --queues={}'.format(queues)
    if concurrency:
        cmd = cmd + ' --concurrency={}'.format(concurrency)
    if max_tasks_per_child:
        cmd = cmd + ' --maxtasksperchild={}'.format(max_tasks_per_child)
    ctx.run(bin_prefix(cmd), pty=True)


@task(aliases=['beat'])
def celery_beat(ctx, level='debug', schedule=None):
    """Run the Celery process."""
    os.environ['DJANGO_SETTINGS_MODULE'] = 'api.base.settings'
    # beat sets up a cron like scheduler, refer to website/settings
    cmd = 'celery beat -A framework.celery_tasks -l {0} --pidfile='.format(level)
    if schedule:
        cmd = cmd + ' --schedule={}'.format(schedule)
    ctx.run(bin_prefix(cmd), pty=True)


@task
def rabbitmq(ctx):
    """Start a local rabbitmq server.

    NOTE: this is for development only. The production environment should start
    the server as a daemon.
    """
    ctx.run('rabbitmq-server', pty=True)


@task(aliases=['elastic'])
def elasticsearch(ctx):
    """Start a local elasticsearch server

    NOTE: Requires that elasticsearch is installed. See README for instructions
    """
    import platform
    if platform.linux_distribution()[0] == 'Ubuntu':
        ctx.run('sudo service elasticsearch start')
    elif platform.system() == 'Darwin':  # Mac OSX
        ctx.run('elasticsearch')
    else:
        print('Your system is not recognized, you will have to start elasticsearch manually')

@task
def migrate_search(ctx, delete=False, index=settings.ELASTIC_INDEX):
    """Migrate the search-enabled models."""
    from website.app import init_app
    init_app(routes=False, set_backends=False)
    from website.search_migration.migrate import migrate

    # NOTE: Silence the warning:
    # "InsecureRequestWarning: Unverified HTTPS request is being made. Adding certificate verification is strongly advised."
    SILENT_LOGGERS = ['py.warnings']
    for logger in SILENT_LOGGERS:
        logging.getLogger(logger).setLevel(logging.ERROR)

    migrate(delete, index=index)


@task
def rebuild_search(ctx):
    """Delete and recreate the index for elasticsearch"""
    from website.app import init_app
    import requests
    from website import settings

    init_app(routes=False, set_backends=True)
    if not settings.ELASTIC_URI.startswith('http'):
        protocol = 'http://' if settings.DEBUG_MODE else 'https://'
    else:
        protocol = ''
    url = '{protocol}{uri}/{index}'.format(
        protocol=protocol,
        uri=settings.ELASTIC_URI.rstrip('/'),
        index=settings.ELASTIC_INDEX,
    )
    print('Deleting index {}'.format(settings.ELASTIC_INDEX))
    print('----- DELETE {}*'.format(url))
    requests.delete(url + '*')
    print('Creating index {}'.format(settings.ELASTIC_INDEX))
    print('----- PUT {}'.format(url))
    requests.put(url)
    migrate_search(ctx)


@task
def mailserver(ctx, port=1025):
    """Run a SMTP test server."""
    cmd = 'python -m smtpd -n -c DebuggingServer localhost:{port}'.format(port=port)
    ctx.run(bin_prefix(cmd), pty=True)


@task
def jshint(ctx):
    """Run JSHint syntax check"""
    js_folder = os.path.join(HERE, 'website', 'static', 'js')
    jshint_bin = os.path.join(HERE, 'node_modules', '.bin', 'jshint')
    cmd = '{} {}'.format(jshint_bin, js_folder)
    ctx.run(cmd, echo=True)


@task(aliases=['flake8'])
def flake(ctx):
    ctx.run('flake8 .', echo=True)


@task(aliases=['req'])
def requirements(ctx, base=False, addons=False, release=False, dev=False, quick=False):
    """Install python dependencies.

    Examples:
        inv requirements
        inv requirements --quick

    Quick requirements are, in order, addons, dev and the base requirements. You should be able to use --quick for
    day to day development.

    By default, base requirements will run. However, if any set of addons, release, or dev are chosen, base
    will have to be mentioned explicitly in order to run. This is to remain compatible with previous usages. Release
    requirements will prevent dev, and base from running.
    """
    if quick:
        base = True
        addons = True
        dev = True
    if not(addons or dev):
        base = True
    if release or addons:
        addon_requirements(ctx)
    # "release" takes precedence
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
        ctx.run(
            pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
            echo=True
        )
    else:
        if dev:  # then dev requirements
            req_file = os.path.join(HERE, 'requirements', 'dev.txt')
            ctx.run(
                pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )

        if base:  # then base requirements
            req_file = os.path.join(HERE, 'requirements.txt')
            ctx.run(
                pip_install(req_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )
    # fix URITemplate name conflict h/t @github
    ctx.run('pip uninstall uritemplate.py --yes || true')
    ctx.run('pip install --no-cache-dir uritemplate.py==0.3.0')


@task
def test_module(ctx, module=None, numprocesses=None, params=None):
    """Helper for running tests.
    """
    os.environ['DJANGO_SETTINGS_MODULE'] = 'osf_tests.settings'
    import pytest
    if not numprocesses:
        from multiprocessing import cpu_count
        numprocesses = cpu_count()
    # NOTE: Subprocess to compensate for lack of thread safety in the httpretty module.
    # https://github.com/gabrielfalcao/HTTPretty/issues/209#issue-54090252
    args = ['-s']
    if numprocesses > 1:
        args += ['-n {}'.format(numprocesses), '--max-slave-restart=0']
    modules = [module] if isinstance(module, basestring) else module
    args.extend(modules)
    if params:
        params = [params] if isinstance(params, basestring) else params
        args.extend(params)
    retcode = pytest.main(args)
    sys.exit(retcode)

OSF_TESTS = [
    'osf_tests',
]

ELSE_TESTS = [
    'tests',
]

API_TESTS1 = [
    'api_tests/identifiers',
    'api_tests/institutions',
    'api_tests/licenses',
    'api_tests/logs',
    'api_tests/metaschemas',
    'api_tests/preprint_providers',
    'api_tests/preprints',
    'api_tests/registrations',
    'api_tests/users',
]
API_TESTS2 = [
    'api_tests/nodes',
]
API_TESTS3 = [
    'api_tests/addons_tests',
    'api_tests/applications',
    'api_tests/base',
    'api_tests/collections',
    'api_tests/comments',
    'api_tests/files',
    'api_tests/guids',
    'api_tests/reviews',
    'api_tests/search',
    'api_tests/taxonomies',
    'api_tests/test',
    'api_tests/tokens',
    'api_tests/view_only_links',
    'api_tests/wikis',
]
ADDON_TESTS = [
    'addons',
]
ADMIN_TESTS = [
    'admin_tests',
]


@task
def test_osf(ctx, numprocesses=None):
    """Run the OSF test suite."""
    print('Testing modules "{}"'.format(OSF_TESTS + ADDON_TESTS))
    test_module(ctx, module=OSF_TESTS + ADDON_TESTS, numprocesses=numprocesses)

@task
def test_else(ctx, numprocesses=None):
    """Run the old test suite."""
    print('Testing modules "{}"'.format(ELSE_TESTS))
    test_module(ctx, module=ELSE_TESTS, numprocesses=numprocesses)

@task
def test_api1(ctx, numprocesses=None):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS1 + ADMIN_TESTS))
    test_module(ctx, module=API_TESTS1 + ADMIN_TESTS, numprocesses=numprocesses)


@task
def test_api2(ctx, numprocesses=None):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS2))
    test_module(ctx, module=API_TESTS2, numprocesses=numprocesses)


@task
def test_api3(ctx, numprocesses=None):
    """Run the API test suite."""
    print('Testing modules "{}"'.format(API_TESTS3))
    test_module(ctx, module=API_TESTS3, numprocesses=numprocesses)


@task
def test_admin(ctx, numprocesses=None):
    """Run the Admin test suite."""
    print('Testing module "admin_tests"')
    test_module(ctx, module=ADMIN_TESTS, numprocesses=numprocesses)


@task
def test_addons(ctx, numprocesses=None):
    """Run all the tests in the addons directory.
    """
    print('Testing modules "{}"'.format(ADDON_TESTS))
    test_module(ctx, module=ADDON_TESTS, numprocesses=numprocesses)


@task
def test_varnish(ctx):
    """Run the Varnish test suite."""
    proc = apiserver(ctx, wait=False, autoreload=False)
    try:
        sleep(5)
        test_module(ctx, module='api/caching/tests/test_caching.py')
    finally:
        proc.kill()


@task
def test(ctx, all=False, syntax=False):
    """
    Run unit tests: OSF (always), plus addons and syntax checks (optional)
    """
    if syntax:
        flake(ctx)
        jshint(ctx)

    test_osf(ctx)
    test_api1(ctx)
    test_api2(ctx)
    test_api3(ctx)

    if all:
        test_addons(ctx)
        # TODO: Enable admin tests
        test_admin(ctx)
        karma(ctx)


@task
def test_js(ctx):
    jshint(ctx)
    karma(ctx)

@task
def test_travis_osf(ctx, numprocesses=None):
    """
    Run half of the tests to help travis go faster. Lints and Flakes happen everywhere to keep from wasting test time.
    """
    flake(ctx)
    jshint(ctx)
    test_osf(ctx, numprocesses=numprocesses)


@task
def test_travis_else(ctx, numprocesses=None):
    """
    Run other half of the tests to help travis go faster. Lints and Flakes happen everywhere to keep from
    wasting test time.
    """
    flake(ctx)
    jshint(ctx)
    test_else(ctx, numprocesses=numprocesses)


@task
def test_travis_api1_and_js(ctx, numprocesses=None):
    flake(ctx)
    jshint(ctx)
    karma(ctx)
    test_api1(ctx, numprocesses=numprocesses)


@task
def test_travis_api2(ctx, numprocesses=None):
    flake(ctx)
    jshint(ctx)
    test_api2(ctx, numprocesses=numprocesses)


@task
def test_travis_api3(ctx, numprocesses=None):
    flake(ctx)
    jshint(ctx)
    test_api3(ctx, numprocesses=numprocesses)


@task
def test_travis_varnish(ctx):
    """
    Run the fast and quirky JS tests and varnish tests in isolation
    """
    flake(ctx)
    jshint(ctx)
    test_js(ctx)
    test_varnish(ctx)


@task
def karma(ctx):
    """Run JS tests with Karma. Requires Chrome to be installed."""
    ctx.run('yarn test', echo=True)


@task
def wheelhouse(ctx, addons=False, release=False, dev=False, pty=True):
    """Build wheels for python dependencies.

    Examples:

        inv wheelhouse --dev
        inv wheelhouse --addons
        inv wheelhouse --release
    """
    if release or addons:
        for directory in os.listdir(settings.ADDON_PATH):
            path = os.path.join(settings.ADDON_PATH, directory)
            if os.path.isdir(path):
                req_file = os.path.join(path, 'requirements.txt')
                if os.path.exists(req_file):
                    cmd = 'pip wheel --find-links={} -r {} --wheel-dir={} -c {}'.format(
                        WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH, CONSTRAINTS_PATH,
                    )
                    ctx.run(cmd, pty=pty)
    if release:
        req_file = os.path.join(HERE, 'requirements', 'release.txt')
    elif dev:
        req_file = os.path.join(HERE, 'requirements', 'dev.txt')
    else:
        req_file = os.path.join(HERE, 'requirements.txt')
    cmd = 'pip wheel --find-links={} -r {} --wheel-dir={} -c {}'.format(
        WHEELHOUSE_PATH, req_file, WHEELHOUSE_PATH, CONSTRAINTS_PATH,
    )
    ctx.run(cmd, pty=pty)


@task
def addon_requirements(ctx):
    """Install all addon requirements."""
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory)

        requirements_file = os.path.join(path, 'requirements.txt')
        if os.path.isdir(path) and os.path.isfile(requirements_file):
            print('Installing requirements for {0}'.format(directory))
            ctx.run(
                pip_install(requirements_file, constraints_file=CONSTRAINTS_PATH),
                echo=True
            )

    print('Finished installing addon requirements')


@task
def travis_addon_settings(ctx):
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path):
            try:
                open(os.path.join(path, 'local-travis.py'))
                ctx.run('cp {path}/local-travis.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_addon_settings(ctx):
    for directory in os.listdir(settings.ADDON_PATH):
        path = os.path.join(settings.ADDON_PATH, directory, 'settings')
        if os.path.isdir(path) and not os.path.isfile(os.path.join(path, 'local.py')):
            try:
                open(os.path.join(path, 'local-dist.py'))
                ctx.run('cp {path}/local-dist.py {path}/local.py'.format(path=path))
            except IOError:
                pass


@task
def copy_settings(ctx, addons=False):
    # Website settings
    if not os.path.isfile('website/settings/local.py'):
        print('Creating local.py file')
        ctx.run('cp website/settings/local-dist.py website/settings/local.py')

    # Addon settings
    if addons:
        copy_addon_settings(ctx)


@task(aliases=['bower'])
def bower_install(ctx):
    print('Installing bower-managed packages')
    bower_bin = os.path.join(HERE, 'node_modules', '.bin', 'bower')
    ctx.run('{} prune --allow-root'.format(bower_bin), echo=True)
    ctx.run('{} install --allow-root'.format(bower_bin), echo=True)


@task
def docker_init(ctx):
    """Initial docker setup"""
    print('You will be asked for your sudo password to continue...')
    if platform.system() == 'Darwin':  # Mac OSX
        ctx.run('sudo ifconfig lo0 alias 192.168.168.167')
    else:
        print('Your system is not recognized, you will have to setup docker manually')

def ensure_docker_env_setup(ctx):
    if hasattr(os.environ, 'DOCKER_ENV_SETUP') and os.environ['DOCKER_ENV_SETUP'] == '1':
        pass
    else:
        os.environ['WEB_REMOTE_DEBUG'] = '192.168.168.167:11000'
        os.environ['API_REMOTE_DEBUG'] = '192.168.168.167:12000'
        os.environ['WORKER_REMOTE_DEBUG'] = '192.168.168.167:13000'
        os.environ['DOCKER_ENV_SETUP'] = '1'
        docker_init(ctx)

@task
def docker_requirements(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up requirements requirements_mfr requirements_wb')

@task
def docker_appservices(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up assets fakecas elasticsearch tokumx postgres')

@task
def docker_osf(ctx):
    ensure_docker_env_setup(ctx)
    ctx.run('docker-compose up mfr wb web api')

@task
def clear_sessions(ctx, months=1, dry_run=False):
    from website.app import init_app
    init_app(routes=False, set_backends=True)
    from scripts import clear_sessions
    clear_sessions.clear_sessions_relative(months=months, dry_run=dry_run)


# Release tasks

@task
def hotfix(ctx, name, finish=False, push=False):
    """Rename hotfix branch to hotfix/<next-patch-version> and optionally
    finish hotfix.
    """
    print('Checking out master to calculate curent version')
    ctx.run('git checkout master')
    latest_version = latest_tag_info()['current_version']
    print('Current version is: {}'.format(latest_version))
    major, minor, patch = latest_version.split('.')
    next_patch_version = '.'.join([major, minor, str(int(patch) + 1)])
    print('Bumping to next patch version: {}'.format(next_patch_version))
    print('Renaming branch...')

    new_branch_name = 'hotfix/{}'.format(next_patch_version)
    ctx.run('git checkout {}'.format(name), echo=True)
    ctx.run('git branch -m {}'.format(new_branch_name), echo=True)
    if finish:
        ctx.run('git flow hotfix finish {}'.format(next_patch_version), echo=True, pty=True)
    if push:
        ctx.run('git push origin master', echo=True)
        ctx.run('git push --tags', echo=True)
        ctx.run('git push origin develop', echo=True)


@task
def feature(ctx, name, finish=False, push=False):
    """Rename the current branch to a feature branch and optionally finish it."""
    print('Renaming branch...')
    ctx.run('git branch -m feature/{}'.format(name), echo=True)
    if finish:
        ctx.run('git flow feature finish {}'.format(name), echo=True)
    if push:
        ctx.run('git push origin develop', echo=True)


# Adapted from bumpversion
def latest_tag_info():
    try:
        # git-describe doesn't update the git-index, so we do that
        # subprocess.check_output(["git", "update-index", "--refresh"])

        # get info about the latest tag in git
        describe_out = subprocess.check_output([
            'git',
            'describe',
            '--dirty',
            '--tags',
            '--long',
            '--abbrev=40'
        ], stderr=subprocess.STDOUT
        ).decode().split('-')
    except subprocess.CalledProcessError as err:
        raise err
        # logger.warn("Error when running git describe")
        return {}

    info = {}

    if describe_out[-1].strip() == 'dirty':
        info['dirty'] = True
        describe_out.pop()

    info['commit_sha'] = describe_out.pop().lstrip('g')
    info['distance_to_latest_tag'] = int(describe_out.pop())
    info['current_version'] = describe_out.pop().lstrip('v')

    # assert type(info["current_version"]) == str
    assert 0 == len(describe_out)

    return info


# Tasks for generating and bundling SSL certificates
# See http://cosdev.readthedocs.org/en/latest/osf/ops.html for details

@task
def generate_key(ctx, domain, bits=2048):
    cmd = 'openssl genrsa -des3 -out {0}.key {1}'.format(domain, bits)
    ctx.run(cmd)


@task
def generate_key_nopass(ctx, domain):
    cmd = 'openssl rsa -in {domain}.key -out {domain}.key.nopass'.format(
        domain=domain
    )
    ctx.run(cmd)


@task
def generate_csr(ctx, domain):
    cmd = 'openssl req -new -key {domain}.key.nopass -out {domain}.csr'.format(
        domain=domain
    )
    ctx.run(cmd)


@task
def request_ssl_cert(ctx, domain):
    """Generate a key, a key with password removed, and a signing request for
    the specified domain.

    Usage:
    > invoke request_ssl_cert pizza.osf.io
    """
    generate_key(ctx, domain)
    generate_key_nopass(ctx, domain)
    generate_csr(ctx, domain)


@task
def bundle_certs(ctx, domain, cert_path):
    """Concatenate certificates from NameCheap in the correct order. Certificate
    files must be in the same directory.
    """
    cert_files = [
        '{0}.crt'.format(domain),
        'COMODORSADomainValidationSecureServerCA.crt',
        'COMODORSAAddTrustCA.crt',
        'AddTrustExternalCARoot.crt',
    ]
    certs = ' '.join(
        os.path.join(cert_path, cert_file)
        for cert_file in cert_files
    )
    cmd = 'cat {certs} > {domain}.bundle.crt'.format(
        certs=certs,
        domain=domain,
    )
    ctx.run(cmd)


@task
def clean_assets(ctx):
    """Remove built JS files."""
    public_path = os.path.join(HERE, 'website', 'static', 'public')
    js_path = os.path.join(public_path, 'js')
    ctx.run('rm -rf {0}'.format(js_path), echo=True)


@task(aliases=['pack'])
def webpack(ctx, clean=False, watch=False, dev=False, colors=False):
    """Build static assets with webpack."""
    if clean:
        clean_assets(ctx)
    args = ['yarn run webpack-{}'.format('dev' if dev else 'prod')]
    args += ['--progress']
    if watch:
        args += ['--watch']
    if colors:
        args += ['--colors']
    command = ' '.join(args)
    ctx.run(command, echo=True)


@task()
def build_js_config_files(ctx):
    from website import settings
    print('Building JS config files...')
    with open(os.path.join(settings.STATIC_FOLDER, 'built', 'nodeCategories.json'), 'wb') as fp:
        json.dump(settings.NODE_CATEGORY_MAP, fp)
    print('...Done.')


@task()
def assets(ctx, dev=False, watch=False, colors=False):
    """Install and build static assets."""
    command = 'yarn install --frozen-lockfile'
    if not dev:
        command += ' --production'
    ctx.run(command, echo=True)
    bower_install(ctx)
    build_js_config_files(ctx)
    # Always set clean=False to prevent possible mistakes
    # on prod
    webpack(ctx, clean=False, watch=watch, dev=dev, colors=colors)


@task
def generate_self_signed(ctx, domain):
    """Generate self-signed SSL key and certificate.
    """
    cmd = (
        'openssl req -x509 -nodes -days 365 -newkey rsa:2048'
        ' -keyout {0}.key -out {0}.crt'
    ).format(domain)
    ctx.run(cmd)


@task
def update_citation_styles(ctx):
    from scripts import parse_citation_styles
    total = parse_citation_styles.main()
    print('Parsed {} styles'.format(total))


@task
def clean(ctx, verbose=False):
    ctx.run('find . -name "*.pyc" -delete', echo=True)


@task(default=True)
def usage(ctx):
    ctx.run('invoke --list')


### Maintenance Tasks ###

@task
def set_maintenance(ctx, message='', level=1, start=None, end=None):
    from website.app import setup_django
    setup_django()
    from website.maintenance import set_maintenance
    """Creates a maintenance notice.

    Message is required.
    Level defaults to 1. Valid levels are 1 (info), 2 (warning), and 3 (danger).

    Set the time period for the maintenance notice to be displayed.
    If no start or end values are displayed, default to starting now
    and ending 24 hours from now. If no timezone info is passed along,
    everything will be converted to UTC.

    If a given end time results in a start that is after the end, start
    will be changed to be 24 hours before the end time.

    Examples:
        invoke set_maintenance --message 'OSF down for scheduled maintenance.' --start 2016-03-16T15:41:00-04:00
        invoke set_maintenance --message 'Apocalypse' --level 3 --end 2016-03-16T15:41:00-04:00
    """
    state = set_maintenance(message, level, start, end)
    print('Maintenance notice up {} to {}.'.format(state['start'], state['end']))


@task
def unset_maintenance(ctx):
    from website.app import setup_django
    setup_django()
    from website.maintenance import unset_maintenance
    print('Taking down maintenance notice...')
    unset_maintenance()
    print('...Done.')
