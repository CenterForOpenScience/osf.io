# encoding: utf-8
#
# Copyright (c) 2010 Doug Hellmann.  All rights reserved.
#
"""virtualenvwrapper.project
"""

import logging
import os

from virtualenvwrapper.user_scripts import make_hook, run_global

log = logging.getLogger(__name__)

GLOBAL_HOOKS = [
    # mkproject
    ("premkproject",
     "This hook is run after a new project is created "
     "and before it is activated."),
    ("postmkproject",
     "This hook is run after a new project is activated."),
]


def initialize(args):
    """Set up user hooks
    """
    for filename, comment in GLOBAL_HOOKS:
        make_hook(os.path.join('$VIRTUALENVWRAPPER_HOOK_DIR', filename),
                  comment)
    return


def pre_mkproject(args):
    log.debug('pre_mkproject %s', str(args))
    run_global('premkproject', *args)
    return


def post_mkproject_source(args):
    return """
#
# Run user-provided scripts
#
[ -f "$WORKON_HOME/postmkproject" ] && source "$WORKON_HOME/postmkproject"
"""


def post_activate_source(args):
    return """
#
# Change to the project directory
#
[ -f "$VIRTUAL_ENV/$VIRTUALENVWRAPPER_PROJECT_FILENAME" ] && \
    virtualenvwrapper_cd \
        "$(cat \"$VIRTUAL_ENV/$VIRTUALENVWRAPPER_PROJECT_FILENAME\")"
"""
