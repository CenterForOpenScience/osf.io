import os
import logging
import tempfile

from addons.base.lock import Lock

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

#############################################################
LOCK_RUN = Lock(TMPDIR, LOCK_PREFIX, 'RUN')
LOCK_PLAN = Lock(TMPDIR, LOCK_PREFIX, 'PLAN')

def init_lock():
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
