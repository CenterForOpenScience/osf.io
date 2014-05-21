# encoding: utf-8
#
# Copyright (c) 2010 Doug Hellmann.  All rights reserved.
#
"""Plugin to handle hooks in user-defined scripts.
"""

import logging
import os
import re
import stat
import subprocess
import sys


log = logging.getLogger(__name__)

# Are we running under msys
if sys.platform == 'win32' and \
   os.environ.get('OS') == 'Windows_NT' and \
   os.environ.get('MSYSTEM') == 'MINGW32':
    is_msys = True
    script_folder = 'Scripts'
else:
    is_msys = False
    script_folder = 'bin'


def run_script(script_path, *args):
    """Execute a script in a subshell.
    """
    if os.path.exists(script_path):
        cmd = [script_path] + list(args)
        if is_msys:
            cmd = [get_path(os.environ['MSYS_HOME'], 'bin', 'sh.exe')] + cmd
        log.debug('running %s', str(cmd))
        try:
            subprocess.call(cmd)
        except OSError:
            _, msg, _ = sys.exc_info()
            log.error('could not run "%s": %s', script_path, str(msg))
        #log.debug('Returned %s', return_code)
    return


def run_global(script_name, *args):
    """Run a script from $VIRTUALENVWRAPPER_HOOK_DIR.
    """
    script_path = get_path('$VIRTUALENVWRAPPER_HOOK_DIR', script_name)
    run_script(script_path, *args)
    return


PERMISSIONS = stat.S_IRWXU | stat.S_IRWXG | stat.S_IROTH | stat.S_IXOTH


GLOBAL_HOOKS = [
    # initialize
    ("initialize",
     "This hook is run during the startup phase "
     "when loading virtualenvwrapper.sh."),

    # mkvirtualenv
    ("premkvirtualenv",
     "This hook is run after a new virtualenv is created "
     "and before it is activated."),
    ("postmkvirtualenv",
     "This hook is run after a new virtualenv is activated."),

    # rmvirtualenv
    ("prermvirtualenv",
     "This hook is run before a virtualenv is deleted."),
    ("postrmvirtualenv",
     "This hook is run after a virtualenv is deleted."),

    # deactivate
    ("predeactivate",
     "This hook is run before every virtualenv is deactivated."),
    ("postdeactivate",
     "This hook is run after every virtualenv is deactivated."),

    # activate
    ("preactivate",
     "This hook is run before every virtualenv is activated."),
    ("postactivate",
     "This hook is run after every virtualenv is activated."),

    # get_env_details
    ("get_env_details",
     "This hook is run when the list of virtualenvs is printed "
     "so each name can include details."),
]


LOCAL_HOOKS = [
    # deactivate
    ("predeactivate",
     "This hook is run before this virtualenv is deactivated."),
    ("postdeactivate",
     "This hook is run after this virtualenv is deactivated."),

    # activate
    ("preactivate",
     "This hook is run before this virtualenv is activated."),
    ("postactivate",
     "This hook is run after this virtualenv is activated."),

    # get_env_details
    ("get_env_details",
     "This hook is run when the list of virtualenvs is printed "
     "in 'long' mode so each name can include details."),
]


def make_hook(filename, comment):
    """Create a hook script.

    :param filename: The name of the file to write.
    :param comment: The comment to insert into the file.
    """
    filename = get_path(filename)
    if not os.path.exists(filename):
        log.info('creating %s', filename)
        f = open(filename, 'w')
        try:
            f.write("#!%(shell)s\n# %(comment)s\n\n" % {
                'comment': comment,
                'shell': os.environ.get('SHELL', '/bin/sh'),
            })
        finally:
            f.close()
        os.chmod(filename, PERMISSIONS)
    return


# HOOKS


def initialize(args):
    for filename, comment in GLOBAL_HOOKS:
        make_hook(get_path('$VIRTUALENVWRAPPER_HOOK_DIR', filename), comment)
    return


def initialize_source(args):
    return """
#
# Run user-provided scripts
#
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/initialize" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/initialize"
"""


def pre_mkvirtualenv(args):
    log.debug('pre_mkvirtualenv %s', str(args))
    envname = args[0]
    for filename, comment in LOCAL_HOOKS:
        make_hook(get_path('$WORKON_HOME', envname, script_folder, filename),
                  comment)
    run_global('premkvirtualenv', *args)
    return


def post_mkvirtualenv_source(args):
    return """
#
# Run user-provided scripts
#
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/postmkvirtualenv" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/postmkvirtualenv"
"""


def pre_cpvirtualenv(args):
    log.debug('pre_cpvirtualenv %s', str(args))
    envname = args[0]
    for filename, comment in LOCAL_HOOKS:
        make_hook(get_path('$WORKON_HOME', envname, script_folder, filename),
                  comment)
    run_global('precpvirtualenv', *args)
    return


def post_cpvirtualenv_source(args):
    return """
#
# Run user-provided scripts
#
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/postcpvirtualenv" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/postcpvirtualenv"
"""


def pre_rmvirtualenv(args):
    log.debug('pre_rmvirtualenv')
    run_global('prermvirtualenv', *args)
    return


def post_rmvirtualenv(args):
    log.debug('post_rmvirtualenv')
    run_global('postrmvirtualenv', *args)
    return


def pre_activate(args):
    log.debug('pre_activate')
    run_global('preactivate', *args)
    script_path = get_path('$WORKON_HOME', args[0],
                           script_folder, 'preactivate')
    run_script(script_path, *args)
    return


def post_activate_source(args):
    log.debug('post_activate')
    return """
#
# Run user-provided scripts
#
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/postactivate" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/postactivate"
[ -f "$VIRTUAL_ENV/$VIRTUALENVWRAPPER_ENV_BIN_DIR/postactivate" ] && \
    source "$VIRTUAL_ENV/$VIRTUALENVWRAPPER_ENV_BIN_DIR/postactivate"
"""


def pre_deactivate_source(args):
    log.debug('pre_deactivate')
    return """
#
# Run user-provided scripts
#
[ -f "$VIRTUAL_ENV/$VIRTUALENVWRAPPER_ENV_BIN_DIR/predeactivate" ] && \
    source "$VIRTUAL_ENV/$VIRTUALENVWRAPPER_ENV_BIN_DIR/predeactivate"
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/predeactivate" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/predeactivate"
"""


def post_deactivate_source(args):
    log.debug('post_deactivate')
    return """
#
# Run user-provided scripts
#
VIRTUALENVWRAPPER_LAST_VIRTUAL_ENV="$WORKON_HOME/%(env_name)s"
[ -f "$WORKON_HOME/%(env_name)s/bin/postdeactivate" ] && \
    source "$WORKON_HOME/%(env_name)s/bin/postdeactivate"
[ -f "$VIRTUALENVWRAPPER_HOOK_DIR/postdeactivate" ] && \
    source "$VIRTUALENVWRAPPER_HOOK_DIR/postdeactivate"
unset VIRTUALENVWRAPPER_LAST_VIRTUAL_ENV
""" % {'env_name': args[0]}


def get_env_details(args):
    log.debug('get_env_details')
    run_global('get_env_details', *args)
    script_path = get_path('$WORKON_HOME', args[0],
                           script_folder, 'get_env_details')
    run_script(script_path, *args)
    return


def get_path(*args):
    '''
    Get a full path from args.

    Path separator is determined according to the os and the shell and
    allow to use is_msys.

    Variables and user are expanded during the process.
    '''
    path = os.path.expanduser(os.path.expandvars(os.path.join(*args)))
    if is_msys:
        # MSYS accept unix or Win32 and sometimes
        # it drives to mixed style paths
        if re.match(r'^/[a-zA-Z](/|^)', path):
            # msys path could starts with '/c/'-form drive letter
            path = ''.join((path[1], ':', path[2:]))
        path = path.replace('/', os.sep)

    return os.path.abspath(path)
