# -*- coding: utf-8 -*-
import pytest

from django.utils.timezone import now

from api.base.settings.defaults import API_BASE
from api_tests.registrations.filters.test_filters import RegistrationListFilteringMixin
from osf_tests.factories import (
    AuthUserFactory,
    CollectionFactory,
    ProjectFactory,
    RegistrationFactory,
)
from tests.base import ApiTestCase
from website.views import find_bookmark_collection


@pytest.mark.django_db
class TestUserRegistrations:

    @pytest.fixture()
    def user_one(self):
        user_one = AuthUserFactory()
        user_one.social['twitter'] = 'rheisendennis'
        user_one.save()
        return user_one

    @pytest.fixture()
    def user_two(self):
        return AuthUserFactory()

    @pytest.fixture()
    def project_public_user_one(self, user_one):
        return ProjectFactory(
            title='Public Project User One',
            is_public=True,
            creator=user_one)

    @pytest.fixture()
    def project_private_user_one(self, user_one):
        return ProjectFactory(
            title='Private Project User One',
            is_public=False,
            creator=user_one)

    @pytest.fixture()
    def project_public_user_two(self, user_two):
        return ProjectFactory(
            title='Public Project User Two',
            is_public=True,
            creator=user_two)

    @pytest.fixture()
    def project_private_user_two(self, user_two):
        return ProjectFactory(
            title='Private Project User Two',
            is_public=False,
            creator=user_two)

    @pytest.fixture()
    def project_deleted_user_one(self, user_one):
        return CollectionFactory(
            title='Deleted Project User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def folder(self):
        return CollectionFactory()

    @pytest.fixture()
    def folder_deleted(self, user_one):
        return CollectionFactory(
            title='Deleted Folder User One',
            is_public=False,
            creator=user_one,
            deleted=now())

    @pytest.fixture()
    def bookmark_collection(self, user_one):
        return find_bookmark_collection(user_one)

    @pytest.fixture()
    def reg_project_public_user_one(self, user_one, project_public_user_one):
        return RegistrationFactory(
            project=project_public_user_one,
            creator=user_one,
            is_public=True)

    @pytest.fixture()
    def reg_project_private_user_one(self, user_one, project_private_user_one):
        return RegistrationFactory(
            project=project_private_user_one,
            creator=user_one,
            is_private=True)

    @pytest.fixture()
    def reg_project_public_user_two(self, user_two, project_public_user_two):
        return RegistrationFactory(
            project=project_public_user_two,
            creator=user_two,
            is_public=True)

    @pytest.fixture()
    def reg_project_private_user_two(self, user_two, project_private_user_two):
        return RegistrationFactory(
            project=project_private_user_two,
            creator=user_two,
            is_private=True)

    def test_user_registrations(
            self, app, user_one, user_two,
            reg_project_public_user_one,
            reg_project_public_user_two,
            reg_project_private_user_one,
            reg_project_private_user_two,
            folder, folder_deleted,
            project_deleted_user_one):

        #   test_authorized_in_gets_200
        url = '/{}users/{}/registrations/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_anonymous_gets_200
        url = '/{}users/{}/registrations/'.format(API_BASE, user_one._id)
        res = app.get(url)
        assert res.status_code == 200
        assert res.content_type == 'application/vnd.api+json'

    #   test_get_registrations_logged_in
        url = '/{}users/{}/registrations/'.format(API_BASE, user_one._id)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert reg_project_public_user_one._id in ids
        assert reg_project_private_user_one._id in ids
        assert reg_project_public_user_two._id not in ids
        assert reg_project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    #   test_get_registrations_not_logged_in
        url = '/{}users/{}/registrations/'.format(API_BASE, user_one._id)
        res = app.get(url)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert reg_project_public_user_one._id in ids
        assert reg_project_private_user_one._id not in ids
        assert reg_project_public_user_two._id not in ids
        assert reg_project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids

    #   test_get_registrations_logged_in_as_different_user
        url = '/{}users/{}/registrations/'.format(API_BASE, user_two._id)
        res = app.get(url, auth=user_one.auth)
        node_json = res.json['data']

        ids = [each['id'] for each in node_json]
        assert reg_project_public_user_one._id not in ids
        assert reg_project_private_user_one._id not in ids
        assert reg_project_public_user_two._id in ids
        assert reg_project_private_user_two._id not in ids
        assert folder._id not in ids
        assert folder_deleted._id not in ids
        assert project_deleted_user_one._id not in ids


class TestRegistrationListFiltering(
        RegistrationListFilteringMixin,
        ApiTestCase):

    url = '/{}users/me/registrations/?'.format(API_BASE)
