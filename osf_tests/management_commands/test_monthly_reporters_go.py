from django.core.management import call_command
from django.test import TestCase
from elasticsearch_metrics.tests.util import djelme_test_backends

from framework.celery_tasks import app as celery_app
from osf_tests import factories


class TestMonthlyReportersGo(TestCase):
    def setUp(self):
        self.enterContext(djelme_test_backends())
        celery_app.conf.update({
            'task_always_eager': True,
            'task_eager_propagates': True,
        })
        # set up data, so each reporter outputs something
        _inst = factories.InstitutionFactory()
        _user = factories.UserFactory()
        _user.add_or_update_affiliated_institution(_inst)
        factories.PreprintFactory()

    def test_for_smoke(self):
        call_command('monthly_reporters_go')
        # TODO: assert more specifically
