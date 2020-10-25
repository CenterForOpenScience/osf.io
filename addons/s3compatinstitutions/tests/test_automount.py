# -*- coding: utf-8 -*-
import unittest
import six

from mock import patch, Mock, MagicMock
import pytest
from nose.tools import *  # noqa (PEP8 asserts)

from admin.rdm_addons.utils import get_rdm_addon_option

from osf_tests.factories import (
    fake_email,
    AuthUserFactory,
    InstitutionFactory,
    ExternalAccountFactory,
    UserFactory,
    ProjectFactory
)
from addons.s3compatinstitutions.models import NodeSettings
from admin_tests.rdm_addons import factories as rdm_addon_factories

USE_MOCK = True  # False for DEBUG

pytestmark = pytest.mark.django_db

NAME = 's3compatinstitutions'
PACKAGE = 'addons.{}'.format(NAME)

DEFAULT_BASE_FOLDER = 'GRDM'
ROOT_FOLDER_FORMAT = '{guid}'

def filename_filter(name):
    return name.replace('/', '_')

class TestS3Compatinstitutions(unittest.TestCase):

    def setUp(self):

        super(TestS3Compatinstitutions, self).setUp()

        self.institution = InstitutionFactory()

        self.user = UserFactory()
        self.user.eppn = fake_email()
        self.user.affiliated_institutions.add(self.institution)
        self.user.save()

        # create
        self.option = get_rdm_addon_option(self.institution.id, NAME)

        account = ExternalAccountFactory(provider=NAME)
        self.option.external_accounts.add(account)

    def _new_project(self):
        if USE_MOCK:
            with patch(PACKAGE + '.models.boto3.client') as mock1:
                mock1.return_value = MagicMock()
                mock1.list_objects.return_value = {'Contents': []}
                # mock1.list_buckets.return_value = None
                self.project = ProjectFactory(creator=self.user)
        else:
            self.project = ProjectFactory(creator=self.user)

    def _allow(self, save=True):
        self.option.is_allowed = True
        if save:
            self.option.save()

    def test_s3compatinstitutions_default_is_not_allowed(self):
        assert_false(self.option.is_allowed)
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_equal(result, None)

    def test_s3compatinstitutions_no_eppn(self):
        self.user.eppn = None
        self.user.save()
        self._allow()
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_equal(result, None)

    def test_s3compatinstitutions_no_institution(self):
        self.user.affiliated_institutions.clear()
        self._allow()
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_equal(result, None)

    def test_s3compatinstitutions_no_addon_option(self):
        self._allow()
        self.option.delete()
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_equal(result, None)

    def test_s3compatinstitutions_automount(self):
        self._allow()
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_true(isinstance(result, NodeSettings))
        name = ROOT_FOLDER_FORMAT.format(
            title=filename_filter(self.project.title),
            guid=self.project._id)
        exptected_root_folder = six.u('{}').format(name)
        assert_equal(result.folder_id, exptected_root_folder)

    def test_s3compatinstitutions_automount_with_basefolder(self):
        base_folder = six.u('GRDM_project_bucket')
        self._allow(save=False)
        self.option.extended = {'base_folder': base_folder}
        self.option.save()
        self._new_project()
        result = self.project.get_addon(NAME)
        assert_true(isinstance(result, NodeSettings))
        name = ROOT_FOLDER_FORMAT.format(
            title=filename_filter(self.project.title),
            guid=self.project._id)
        exptected_root_folder = six.u('{}').format(name)
        assert_equal(result.folder_id, exptected_root_folder)
