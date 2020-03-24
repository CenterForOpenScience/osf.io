import os
import time
import logging
import tempfile
import shutil

logger = logging.getLogger(__name__)

TMPDIR = tempfile.gettempdir()
LOCK_PREFIX = 'GRDM_dropboxbusiness_timestamp_lock_'
PLAN_FILE = os.path.join(TMPDIR, LOCK_PREFIX + 'TEAM_IDS')

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
LOCK_PLAN = Lock('PLAN')

def init_celery_lock():
    LOCK_RUN.unlock()
    LOCK_PLAN.unlock()

def add_plan(team_ids):
    try:
        LOCK_PLAN.lock()
        DEBUG('PLAN_FILE={}'.format(PLAN_FILE))
        with open(PLAN_FILE, 'a') as f:
            for team_id in team_ids:
                f.write(team_id + '\n')
    except Exception as e:
        DEBUG(str(e))
    finally:
        LOCK_PLAN.unlock()

def get_plan(team_ids):
    try:
        new_ids = set(team_ids)
        lines = []
        LOCK_PLAN.lock()
        tmp_lines = []
        with open(PLAN_FILE, 'r') as f:
            tmp_lines = f.readlines()
        for line in tmp_lines:
            lines.append(line.rstrip())
        os.unlink(PLAN_FILE)
    except Exception as e:
        DEBUG(str(e))
    finally:
        LOCK_PLAN.unlock()
    DEBUG('requested team_ids={}'.format(lines))
    new_ids.update(lines)
    return new_ids
