# encoding: utf-8
import json
import pytest

from osf_tests.factories import UserFactory
from osf.models import UserEducation, UserEmployment
from django.db import connection
from osf.management.commands.migrate_education_employment import populate_new_models


@pytest.mark.django_db
class TestEducationEmploymentInfoMigration:

    @pytest.fixture()
    def user(self):
        user = UserFactory()
        user.save()
        schools = [
            {
                u'degree': u'BA Communications',
                u'department': u'Communications',
                u'endMonth': None,
                u'endYear': 1996,
                u'institution': u'Clemson',
                u'ongoing': False,
                u'startMonth': None,
                u'startYear': 1973
            }
        ]
        jobs = [
            {
                u'title': u'Safety',
                u'department': u'Defense',
                u'endMonth': None,
                u'endYear': 2008,
                u'institution': u'Philadelphia Eagles',
                u'ongoing': False,
                u'startMonth': None,
                u'startYear': 1996
            }, {
                u'title': u'Hall of Fame Safety',
                u'department': u'Defense',
                u'institution': u'Philadelphia Eagles',
                u'ongoing': True,
                u'startYear': 2018
            }
        ]

        # Need to make a this a raw slq insert because the model level fields are deleted
        with connection.cursor() as cursor:
            cursor.execute('UPDATE osf_osfuser SET jobs = %s, schools = %s WHERE id = %s', [json.dumps(jobs), json.dumps(schools), user.id])

        return user

    @pytest.fixture()
    def user2(self):
        """
        endMonth was set to zero instead of null for many users.
        :return:
        """
        user = UserFactory()
        user.save()
        schools = [
            {
                u'degree': '',
                u'department': '',
                u'endMonth': 0,
                u'endYear': '',
                u'institution': u'Enfield Tennis Academy',
                u'ongoing': False,
                u'startMonth': None,
                u'startYear': ''
            }
        ]

        # Need to make a this a raw slq insert because the model level fields are deleted
        with connection.cursor() as cursor:
            cursor.execute('UPDATE osf_osfuser SET schools = %s WHERE id = %s', [json.dumps(schools), user.id])

        return user

    def test_education_employment_migration(self, user, user2):
        populate_new_models(rows=10000, dry_run=False)
        education_info = UserEducation.objects.all()
        assert education_info.count() == 2

        education_info = UserEmployment.objects.all()
        assert education_info.count() == 2

        education_info = UserEmployment.objects.all()
        for i, info in enumerate(education_info):
            assert info._order == i + 1

        employment_info = UserEmployment.objects.last()
        assert employment_info.title == 'Hall of Fame Safety'
