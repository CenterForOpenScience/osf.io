import os
import time
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)

TMPDIR = tempfile.gettempdir()
LOCK_PREFIX = 'GRDM_nextcloudinstitutions_timestamp_lock_'

ENABLE_DEBUG = False

def DEBUG(msg):
    if ENABLE_DEBUG:
        logger.error(u'DEBUG: ' + msg)
    else:
        logger.debug(msg)

class Lock():
    def __init__(self, purpose):
        self.lockdir = os.path.join(TMPDIR, LOCK_PREFIX + purpose)

    def trylock(self):
        try:
            os.mkdir(self.lockdir)  # atomic operation
            DEBUG('(try)lock: ' + self.lockdir)
            return True
        except Exception as e:
            DEBUG(str(e))
            return False

    def lock(self):
        if not self.trylock():
            time.sleep(1)
        return True

    def unlock(self):
        try:
            shutil.rmtree(self.lockdir)
            DEBUG('unlock: ' + self.lockdir)
        except Exception as e:
            DEBUG(str(e))


#############################################################
LOCK_RUN = Lock('RUN')

def init_celery_lock():
    LOCK_RUN.unlock()
