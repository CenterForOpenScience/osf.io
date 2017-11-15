# -*- coding: utf-8 -*-
import pytest

from osf.models import QuickFilesNode
from osf_tests.factories import AuthUserFactory

from tests.base import test_app
from webtest_plus import TestApp
from addons.osfstorage.tests.utils import make_payload
from addons.osfstorage.models import OsfStorageFile

from framework.auth import signing


@pytest.fixture()
def user():
    return AuthUserFactory()


@pytest.fixture()
def quickfiles(user):
    return QuickFilesNode.objects.get(creator=user)


@pytest.fixture()
def flask_app():
    return TestApp(test_app)


@pytest.fixture()
def post_to_quickfiles(quickfiles, user, flask_app, **kwargs):
    def func(name, *args, **kwargs):
        osfstorage = quickfiles.get_addon('osfstorage')
        root = osfstorage.get_root()
        url = '/api/v1/project/{}/osfstorage/{}/children/'.format(quickfiles._id, root._id)
        expect_errors = kwargs.pop('expect_errors', False)
        payload = make_payload(user=user, name=name, **kwargs)

        res = flask_app.post_json(url, signing.sign_data(signing.default_signer, payload), expect_errors=expect_errors)
        return res

    return func


@pytest.mark.django_db
class TestUserQuickFilesNodeFileCreation:

    def test_create_file(self, quickfiles, user, post_to_quickfiles):
        name = 'WoopThereItIs.pdf'

        res = post_to_quickfiles(name)

        assert res.status_code == 201
        assert res.json['status'] == 'success'
        assert OsfStorageFile.objects.filter(node__creator=user, name=name).exists()

    def test_create_folder_throws_error(self, flask_app, user, quickfiles, post_to_quickfiles):
        name = 'new_illegal_folder'
        res = post_to_quickfiles(name, kind='folder', expect_errors=True)

        assert res.status_code == 400
