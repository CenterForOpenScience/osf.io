"""Utilities for annotating workshop RSVP data.

Example ::

    import pandas as pd
    from scripts import annotate_rsvps
    frame = pd.read_csv('workshop.csv')
    annotated = annotate_rsvps.process(frame)
    annotated.to_csv('workshop-annotated.csv')

"""

import re
import logging

from dateutil.parser import parse as parse_date

from modularodm import Q
from modularodm.exceptions import ModularOdmException

from osf.models import OSFUser, AbstractNode, NodeLog


logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


def find_by_email(email):
    try:
        return OSFUser.find_one(Q('username', 'iexact', email))
    except ModularOdmException:
        return None


def find_by_name(name):
    try:
        parts = re.split(r'\s+', name.strip())
    except:
        return None
    if len(parts) < 2:
        return None
    users = OSFUser.find(
        reduce(
            lambda acc, value: acc & value,
            [
                Q('fullname', 'icontains', part.decode('utf-8', 'ignore'))
                for part in parts
            ]
        )
    ).sort('-date_created')
    if not users:
        return None
    if len(users) > 1:
        logger.warn('Multiple users found for name {}'.format(name))
    return users[0]


def logs_since(user, date):
    return NodeLog.find(
        Q('user', 'eq', user._id) &
        Q('date', 'gt', date)
    )


def nodes_since(user, date):
    return AbstractNode.find(
        Q('creator', 'eq', user._id) &
        Q('date_created', 'gt', date)
    )


def process(frame):
    frame = frame.copy()
    frame['user_id'] = ''
    frame['user_logs'] = ''
    frame['user_nodes'] = ''
    frame['last_log'] = ''
    for idx, row in frame.iterrows():
        user = (
            find_by_email(row['Email address'].strip()) or
            find_by_name(row['Name'])
        )
        if user:
            date = parse_date(row['Workshop_date'])
            frame.loc[idx, 'user_id'] = user._id
            logs = logs_since(user, date)
            frame.loc[idx, 'user_logs'] = logs.count()
            frame.loc[idx, 'user_nodes'] = nodes_since(user, date).count()
            if logs:
                frame.loc[idx, 'last_log'] = logs.sort('-date')[0].date.strftime('%c')
    return frame
