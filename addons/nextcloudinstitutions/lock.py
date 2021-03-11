import os
import logging
import glob
import tempfile
import shutil

logger = logging.getLogger(__name__)

TMPDIR = tempfile.gettempdir()
LOCK_PREFIX = 'GRDM_nextcloudinstitutions_timestamp_lock_'

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG_nextcloudinstitutions: ' + msg)
    else:
        logger.debug(msg)


def init_lock():
    dirs = glob.glob(os.path.join(TMPDIR, LOCK_PREFIX + '*'))
    DEBUG('dirs: {}'.format(str(dirs)))
    for d in dirs:
        shutil.rmtree(d)
