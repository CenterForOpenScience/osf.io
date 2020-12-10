import os
import time
import shutil
import logging

logger = logging.getLogger(__name__)

class Lock(object):
    def __init__(self, tmpdir, prefix, purpose):
        self.lockdir = os.path.join(tmpdir, prefix + purpose)

    def trylock(self):
        try:
            os.mkdir(self.lockdir)  # atomic operation
            return True
        except Exception:
            logger.debug('(try)lock failed')
            return False

    def lock(self):
        while not self.trylock():
            time.sleep(1)
        return True

    def unlock(self):
        try:
            shutil.rmtree(self.lockdir)
        except Exception:
            logger.warning('unlock failed')
