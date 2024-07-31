import os

from invoke import task

from website import settings

HERE = os.path.dirname(os.path.abspath(__file__))
WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')


@task()
def manage(ctx, cmd_str):
    """Take command string for manage commands

    :param cmd_str: ex. runserver, migrate, "migrate module"
    """
    manage_cmd = os.path.join(HERE, '..', 'manage.py')
    env = 'DJANGO_SETTINGS_MODULE="admin.base.settings"'
    cmd = f'{env} python {manage_cmd} {cmd_str}'
    ctx.run(cmd, echo=True, pty=True)


@task()
def assets(ctx, dev=False, watch=False):
    """Install and build static assets for admin.

    use -d for dev environments
    """
    if os.getcwd() != HERE:
        os.chdir(HERE)
    command = 'yarn install --frozen-lockfile'
    if not dev:
        command += ' --production'
    ctx.run(command, echo=True)
    bower_install(ctx)
    # Always set clean=False to prevent possible mistakes
    # on prod
    webpack(ctx, clean=False, watch=watch, dev=dev)


@task(aliases=['pack'])
def webpack(ctx, clean=False, watch=False, dev=False):
    """Build static assets with webpack."""
    if clean:
        clean_assets(ctx)
    if os.getcwd() != HERE:
        os.chdir(HERE)
    webpack_bin = os.path.join(HERE, 'node_modules', 'webpack', 'bin',
                               'webpack.js')
    args = [webpack_bin]
    if settings.DEBUG_MODE and dev:
        args += ['--colors']
    else:
        args += ['--progress']
    if watch:
        args += ['--watch']
    config_file = 'webpack.admin.config.js' if dev else 'webpack.prod.config.js'
    args += [f'--config {config_file}']
    command = ' '.join(args)
    ctx.run(command, echo=True)


@task
def clean_assets(ctx):
    """Remove built JS files."""
    public_path = os.path.join(HERE, 'static', 'public')
    js_path = os.path.join(public_path, 'js')
    ctx.run(f'rm -rf {js_path}', echo=True)


@task(aliases=['bower'])
def bower_install(ctx):
    if os.getcwd() != HERE:
        os.chdir(HERE)
    bower_bin = os.path.join(HERE, 'node_modules', 'bower', 'bin', 'bower')
    ctx.run(f'{bower_bin} prune --allow-root', echo=True)
    ctx.run(f'{bower_bin} install --allow-root', echo=True)
