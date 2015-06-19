"""
Adds time_to_send field to digest documents.
Assumes all currently unsent digests are slated for release at midnight UTC. Checks if they are more than a day old?
"""

import logging
from website import models
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    pass


def migrate_add_send_time():
    success_count = 0
    fail_count = 0
    old_count = 0

