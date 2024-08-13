import os
import sys

WHEELHOUSE_PATH = os.environ.get('WHEELHOUSE')

def get_bin_path():
    """Get parent path of current python binary.
    """
    return os.path.dirname(sys.executable)


def bin_prefix(cmd):
    """Prefix command with current binary path.
    """
    return os.path.join(get_bin_path(), cmd)


def pip_install(req_file, constraints_file=None):
    """
    Return the proper 'pip install' command for installing the dependencies
    defined in ``req_file``. Optionally obey a file of constraints in case of version conflicts
    """
    cmd = bin_prefix(f'pip3 install --exists-action w --upgrade -r {req_file} ')
    if constraints_file:  # Support added in pip 7.1
        cmd += f' -c {constraints_file}'

    if WHEELHOUSE_PATH:
        cmd += f' --no-index --find-links={WHEELHOUSE_PATH}'
    return cmd
