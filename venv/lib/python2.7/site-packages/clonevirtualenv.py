from __future__ import with_statement
import logging
import optparse
import os
import re
import shutil
import subprocess
import sys

version_info = (0, 2, 4)
__version__ = '.'.join(map(str, version_info))


logger = logging.getLogger()


if sys.version_info < (2, 6):
    next = lambda gen: gen.next()


env_bin_dir = 'bin'
if sys.platform == 'win32':
    env_bin_dir = 'Scripts'


class UserError(Exception):
    pass


def _dirmatch(path, matchwith):
    """Check if path is within matchwith's tree.

    >>> _dirmatch('/home/foo/bar', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar/', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar/etc', '/home/foo/bar')
    True
    >>> _dirmatch('/home/foo/bar2', '/home/foo/bar')
    False
    >>> _dirmatch('/home/foo/bar2/etc', '/home/foo/bar')
    False
    """
    matchlen = len(matchwith)
    if (path.startswith(matchwith)
        and path[matchlen:matchlen + 1] in [os.sep, '']):
        return True
    return False


def _virtualenv_sys(venv_path):
    "obtain version and path info from a virtualenv."
    executable = os.path.join(venv_path, env_bin_dir, 'python')
    # Must use "executable" as the first argument rather than as the
    # keyword argument "executable" to get correct value from sys.path
    p = subprocess.Popen([executable,
        '-c', 'import sys;'
              'print (sys.version[:3]);'
              'print ("\\n".join(sys.path));'],
        env={},
        stdout=subprocess.PIPE)
    stdout, err = p.communicate()
    assert not p.returncode and stdout
    lines = stdout.decode('utf-8').splitlines()
    return lines[0], filter(bool, lines[1:])


def clone_virtualenv(src_dir, dst_dir):
    if not os.path.exists(src_dir):
        raise UserError('src dir %r does not exist' % src_dir)
    if os.path.exists(dst_dir):
        raise UserError('dest dir %r exists' % dst_dir)
    #sys_path = _virtualenv_syspath(src_dir)
    logger.info('cloning virtualenv \'%s\' => \'%s\'...' %
            (src_dir, dst_dir))
    shutil.copytree(src_dir, dst_dir, symlinks=True,
            ignore=shutil.ignore_patterns('*.pyc'))
    version, sys_path = _virtualenv_sys(dst_dir)
    logger.info('fixing scripts in bin...')
    fixup_scripts(src_dir, dst_dir, version)

    has_old = lambda s: any(i for i in s if _dirmatch(i, src_dir))

    if has_old(sys_path):
        # only need to fix stuff in sys.path if we have old
        # paths in the sys.path of new python env. right?
        logger.info('fixing paths in sys.path...')
        fixup_syspath_items(sys_path, src_dir, dst_dir)
    v_sys = _virtualenv_sys(dst_dir)
    remaining = has_old(v_sys[1])
    assert not remaining, v_sys


def fixup_scripts(old_dir, new_dir, version, rewrite_env_python=False):
    bin_dir = os.path.join(new_dir, env_bin_dir)
    root, dirs, files = next(os.walk(bin_dir))
    pybinre = re.compile('pythonw?([0-9]+(\.[0-9]+(\.[0-9]+)?)?)?$')
    for file_ in files:
        filename = os.path.join(root, file_)
        if file_ in ['python', 'python%s' % version, 'activate_this.py']:
            continue
        elif file_.startswith('python') and pybinre.match(file_):
            # ignore other possible python binaries
            continue
        elif file_.endswith('.pyc'):
            # ignore compiled files
            continue
        elif file_ == 'activate' or file_.startswith('activate.'):
            fixup_activate(os.path.join(root, file_), old_dir, new_dir)
        elif os.path.islink(filename):
            fixup_link(filename, old_dir, new_dir)
        elif os.path.isfile(filename):
            fixup_script_(root, file_, old_dir, new_dir, version,
                rewrite_env_python=rewrite_env_python)


def fixup_script_(root, file_, old_dir, new_dir, version,
                  rewrite_env_python=False):
    old_shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(old_dir))
    new_shebang = '#!%s/bin/python' % os.path.normcase(os.path.abspath(new_dir))
    env_shebang = '#!/usr/bin/env python'

    filename = os.path.join(root, file_)
    with open(filename, 'rb') as f:
        if f.read(2) != b'#!':
            # no shebang
            return
        f.seek(0)
        lines = f.readlines()

    if not lines:
        # warn: empty script
        return

    def rewrite_shebang(version=None):
        logger.debug('fixing %s' % filename)
        shebang = new_shebang
        if version:
            shebang = shebang + version
        shebang = (shebang + '\n').encode('utf-8')
        with open(filename, 'wb') as f:
            f.write(shebang)
            f.writelines(lines[1:])

    try:
        bang = lines[0].decode('utf-8').strip()
    except UnicodeDecodeError:
        # binary file
        return

    if not bang.startswith('#!'):
        return
    elif bang == old_shebang:
        rewrite_shebang()
    elif (bang.startswith(old_shebang)
          and bang[len(old_shebang):] == version):
        rewrite_shebang(version)
    elif rewrite_env_python and bang.startswith(env_shebang):
        if bang == env_shebang:
            rewrite_shebang()
        elif bang[len(env_shebang):] == version:
            rewrite_shebang(version)
    else:
        # can't do anything
        return


def fixup_activate(filename, old_dir, new_dir):
    logger.debug('fixing %s' % filename)
    with open(filename, 'rb') as f:
        data = f.read().decode('utf-8')

    data = data.replace(old_dir, new_dir)
    with open(filename, 'wb') as f:
        f.write(data.encode('utf-8'))


def fixup_link(filename, old_dir, new_dir, target=None):
    logger.debug('fixing %s' % filename)
    if target is None:
        target = os.readlink(filename)

    origdir = os.path.dirname(os.path.abspath(filename)).replace(
        new_dir, old_dir)
    if not os.path.isabs(target):
        target = os.path.abspath(os.path.join(origdir, target))
        rellink = True
    else:
        rellink = False

    if _dirmatch(target, old_dir):
        if rellink:
            # keep relative links, but don't keep original in case it
            # traversed up out of, then back into the venv.
            # so, recreate a relative link from absolute.
            target = target[len(origdir):].lstrip(os.sep)
        else:
            target = target.replace(old_dir, new_dir, 1)

    # else: links outside the venv, replaced with absolute path to target.
    _replace_symlink(filename, target)


def _replace_symlink(filename, newtarget):
    tmpfn = "%s.new" % filename
    os.symlink(newtarget, tmpfn)
    os.rename(tmpfn, filename)


def fixup_syspath_items(syspath, old_dir, new_dir):
    for path in syspath:
        if not os.path.isdir(path):
            continue
        path = os.path.normcase(os.path.abspath(path))
        if _dirmatch(path, old_dir):
            path = path.replace(old_dir, new_dir, 1)
            if not os.path.exists(path):
                continue
        elif not _dirmatch(path, new_dir):
            continue
        root, dirs, files = next(os.walk(path))
        for file_ in files:
            filename = os.path.join(root, file_)
            if filename.endswith('.pth'):
                fixup_pth_file(filename, old_dir, new_dir)
            elif filename.endswith('.egg-link'):
                fixup_egglink_file(filename, old_dir, new_dir)


def fixup_pth_file(filename, old_dir, new_dir):
    logger.debug('fixing %s' % filename)
    with open(filename, 'rb') as f:
        lines = f.readlines()
    has_change = False
    for num, line in enumerate(lines):
        line = line.decode('utf-8').strip()
        if not line or line.startswith('#') or line.startswith('import '):
            continue
        elif _dirmatch(line, old_dir):
            lines[num] = line.replace(old_dir, new_dir, 1)
            has_change = True
    if has_change:
        with open(filename, 'wb') as f:
            f.writelines(lines)


def fixup_egglink_file(filename, old_dir, new_dir):
    logger.debug('fixing %s' % filename)
    with open(filename, 'rb') as f:
        link = f.read().decode('utf-8').strip()
    if _dirmatch(link, old_dir):
        link = link.replace(old_dir, new_dir, 1)
        with open(filename, 'wb') as f:
            link = (link + '\n').encode('utf-8')
            f.write(link)


def main():
    parser = optparse.OptionParser("usage: %prog [options]"
        " /path/to/existing/venv /path/to/cloned/venv")
    parser.add_option('-v',
            action="count",
            dest='verbose',
            default=False,
            help='verbosity')
    options, args = parser.parse_args()
    try:
        old_dir, new_dir = args
    except ValueError:
        parser.error("not enough arguments given.")
    old_dir = os.path.normpath(os.path.abspath(old_dir))
    new_dir = os.path.normpath(os.path.abspath(new_dir))
    loglevel = (logging.WARNING, logging.INFO, logging.DEBUG)[min(2,
            options.verbose)]
    logging.basicConfig(level=loglevel, format='%(message)s')
    try:
        clone_virtualenv(old_dir, new_dir)
    except UserError:
        e = sys.exc_info()[1]
        parser.error(str(e))


if __name__ == '__main__':
    main()
