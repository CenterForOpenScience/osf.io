# -*- coding: utf-8 -*-
from django.utils import timezone

from api.base.settings.defaults import API_BASE
from nose.tools import *  # flake8: noqa
from osf_tests.factories import AuthUserFactory, PreprintFactory
from tests.base import ApiTestCase
from datetime import datetime
from osf.utils.workflows import DefaultStates


class PreprintCitationsMixin(object):

    def setUp(self):
        super(PreprintCitationsMixin, self).setUp()
        self.admin_contributor = AuthUserFactory()
        self.published_preprint = PreprintFactory(
            creator=self.admin_contributor)
        self.unpublished_preprint = PreprintFactory(
            creator=self.admin_contributor, is_published=False)

    def test_unauthenticated_can_view_published_preprint_citations(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)

    def test_unauthenticated_cannot_view_unpublished_preprint_citations(self):
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

    def test_preprint_citations_are_read_only(self):
        post_res = self.app.post_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(post_res.status_code, 405)
        put_res = self.app.put_json_api(
            self.published_preprint_url, {},
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(put_res.status_code, 405)
        delete_res = self.app.delete_json_api(
            self.published_preprint_url,
            auth=self.admin_contributor.auth,
            expect_errors=True)
        assert_equal(delete_res.status_code, 405)


class TestPreprintCitations(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitations, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_citation_publisher_is_preprint_provider(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['attributes']['publisher'],
            self.published_preprint.provider.name)

    def test_citation_url_is_preprint_url_not_project(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        assert_equal(
            res.json['data']['links']['self'],
            self.published_preprint.display_absolute_url
        )

class TestPreprintCitationsPermissions(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationsPermissions, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_unpublished_preprint_citations(self):
        # Unauthenticated
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.unpublished_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state, not because of published flag
        assert_equal(res.status_code, 403)

        # Admin contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_private_preprint_citations(self):
        self.published_preprint.is_public = False
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 200)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_deleted_preprint_citations(self):
        self.published_preprint.deleted = timezone.now()
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 404)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 404)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_abandoned_preprint_citations(self):
        self.published_preprint.machine_state = DefaultStates.INITIAL.value
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 403)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_orphaned_preprint_citations(self):
        self.published_preprint.primary_file = None
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 200)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)


class TestPreprintCitationContent(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationContent, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.unpublished_preprint._id)

    def test_citation_contains_correct_date(self):
        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        expected_date = self.published_preprint.logs.latest().created.strftime('%Y, %B %-d')
        assert_true(
            expected_date in res.json['data']['attributes']['citation'])

        self.published_preprint.original_publication_date = datetime(
            2017, 12, 24)
        self.published_preprint.save()

        res = self.app.get(self.published_preprint_url)
        assert_equal(res.status_code, 200)
        expected_date = self.published_preprint.original_publication_date.strftime(
            '%Y, %B %-d')
        assert_true(
            expected_date in res.json['data']['attributes']['citation'])


class TestPreprintCitationsContentPermissions(PreprintCitationsMixin, ApiTestCase):

    def setUp(self):
        super(TestPreprintCitationsContentPermissions, self).setUp()
        self.published_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.published_preprint._id)
        self.unpublished_preprint_url = '/{}preprints/{}/citation/apa/'.format(
            API_BASE, self.unpublished_preprint._id)
        self.other_contrib = AuthUserFactory()

    def test_unpublished_preprint_citations(self):
        # Unauthenticated
        res = self.app.get(self.unpublished_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.unpublished_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.unpublished_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state, not because of published flag
        assert_equal(res.status_code, 403)

        # Admin contrib
        res = self.app.get(self.unpublished_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_private_preprint_citations(self):
        self.published_preprint.is_public = False
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 200)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_deleted_preprint_citations(self):
        self.published_preprint.deleted = timezone.now()
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 404)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 404)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth, expect_errors=True)
        assert_equal(res.status_code, 404)

    def test_abandoned_preprint_citations(self):
        self.published_preprint.machine_state = DefaultStates.INITIAL.value
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 403)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)

    def test_orphaned_preprint_citations(self):
        self.published_preprint.primary_file = None
        self.published_preprint.save()

        # Unauthenticated
        res = self.app.get(self.published_preprint_url, expect_errors=True)
        assert_equal(res.status_code, 401)

        # Non contrib
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth, expect_errors=True)
        assert_equal(res.status_code, 403)

        # Write contrib
        self.published_preprint.add_contributor(self.other_contrib, 'write', save=True)
        res = self.app.get(self.published_preprint_url, auth=self.other_contrib.auth)
        # Really because preprint is in initial machine state
        assert_equal(res.status_code, 200)

        # Admin contrib
        res = self.app.get(self.published_preprint_url, auth=self.admin_contributor.auth)
        assert_equal(res.status_code, 200)
