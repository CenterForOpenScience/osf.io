"""Changes existing profile education and employment dates from
YYYY-MM-DD formatted dates to "Month Year" format

Log:

    Run on production by SL on 2014-10-14 at 19:11 EST. 269 users were migrated.
"""

import logging
from website.app import init_app
from website import models
from datetime import datetime
from tests.base import OsfTestCase
from tests.factories import UserFactory
from nose.tools import *

logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)


def main():
    # Set up storage backends
    init_app(routes=False)
    print ('{n} dates migrated'.format(n=migrate_dates()))


def replace_date(user_field, key, month, year):
    if not isinstance(user_field[key], datetime):
        date = datetime.strptime(user_field[key], '%Y-%m-%d')
    else:
        date = user_field[key]
    user_field[month] = date.month
    user_field[year] = date.year
    del user_field[key]


def migrate_dates():
    count = 0
    for user in models.User.find():
        changed = False
        for job in user.jobs:
            if job.get('start', None):
                replace_date(job, 'start', 'startMonth', 'startYear')
                changed = True
            if job.get('end', None):
                replace_date(job, 'end', 'endMonth', 'endYear')
                changed = True

        for school in user.schools:
            if school.get('start', None):
                replace_date(school, 'start', 'startMonth', 'startYear')
                changed = True
            if school.get('end', None):
                replace_date(school, 'end', 'endMonth', 'endYear')
                changed = True

        if changed:
            logger.info(user)
            count += 1

    logger.info('Process completed. {n} users affected'.format(n=count))
    return count


class TestMigrateDates(OsfTestCase):
    def setUp(self):
        super(TestMigrateDates, self).setUp()
        self.user = UserFactory()
        self.user2 = UserFactory()
        job1 = {
            'position': 'Rockstar',
            'institution': 'Queen',
            'department': 'RocknRoll',
            'location': 'Queens, NY',
            'start': '2014-05-18',
            'end': '2014-09-30',
            'ongoing': False
        }
        job2 = {
            'position': 'Artist',
            'institution': 'Queen',
            'department': 'RocknRoll',
            'location': 'Queens, NY',
            'start': '2014-05-18',
            'end': None,
            'ongoing': True
        }
        school1 = {
            'degree': 'Philosophy',
            'institution': 'Queens University',
            'department': 'Contemplation',
            'location': 'New York, NY',
            'start': '2014-01-01',
            'end': '2014-01-02',
            'ongoing': False
        }
        school2 = {
            'degree': 'Astrophysics',
            'institution': 'Queens University',
            'department': None,
            'location': 'Space',
            'start': '2014-01-01',
            'end': None,
            'ongoing': True
        }

        self.user.jobs.append(job1)
        self.user.jobs.append(job2)
        self.user.schools.append(school1)
        self.user.schools.append(school2)

    def test_migrate_dates(self):
        migrate_dates()
        assert_equal(self.user.jobs[0].get('startMonth'), 5)
        assert_equal(self.user.jobs[0].get('startYear'), 2014)
        assert_equal(self.user.jobs[0].get('endMonth'), 9)
        assert_equal(self.user.jobs[0].get('endYear'), 2014)
        assert_false(self.user.jobs[0].get('start', None))
        assert_false(self.user.jobs[0].get('end', None))

        assert_equal(self.user.jobs[1].get('startMonth'), 5)
        assert_equal(self.user.jobs[1].get('startYear'), 2014)
        assert_equal(self.user.jobs[1].get('endMonth'), None)
        assert_equal(self.user.jobs[1].get('endYear'), None)
        assert_false(self.user.jobs[1].get('start', None))
        assert_false(self.user.jobs[1].get('end', None))

        assert_equal(self.user.schools[0].get('startMonth'), 1)
        assert_equal(self.user.schools[0].get('startYear'), 2014)
        assert_equal(self.user.schools[0].get('endMonth'), 1)
        assert_equal(self.user.schools[0].get('endYear'), 2014)
        assert_false(self.user.schools[0].get('start', None))
        assert_false(self.user.schools[0].get('end', None))

        assert_equal(self.user.schools[1].get('startMonth'), 1)
        assert_equal(self.user.schools[1].get('startYear'), 2014)
        assert_equal(self.user.schools[1].get('endMonth'), None)
        assert_equal(self.user.schools[1].get('endYear'), None)
        assert_false(self.user.schools[1].get('start', None))
        assert_false(self.user.schools[1].get('end', None))

if __name__ == '__main__':
    main()
