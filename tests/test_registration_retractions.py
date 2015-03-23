"""Tests related to retraction of public registrations"""

import datetime
from nose.tools import *  # noqa

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, NodeFactory, RegistrationFactory, UserFactory, AuthUserFactory

import werkzeug
from modularodm.exceptions import ValidationTypeError

from framework.auth.core import Auth
from framework.exceptions import HTTPError

from website.project.decorators import must_be_valid_project


class RegistrationRetractionModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.justification = 'I loathe openness...'

    def test_retract(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user, self.justification)

        self.registration.reload()
        assert_true(self.registration.is_retracted)
        assert_equal(self.registration.retracted_justification, self.justification)
        assert_equal(self.registration.retracted_by, self.user)
        assert_equal(
            self.registration.retraction_date.date(),
            datetime.datetime.utcnow().date()
        )

    def test_retract_private_registration_throws_type_error(self):
        with assert_raises(ValidationTypeError):
            self.registration.retract_registration(self.user, self.justification)

        self.registration.reload()
        assert_false(self.registration.is_retracted)
        assert_is_none(self.registration.retracted_justification)
        assert_is_none(self.registration.retracted_by)
        assert_is_none(self.registration.retraction_date)

    def test_retract_public_non_registration_throws_type_error(self):
        self.project.is_public = True
        with assert_raises(ValidationTypeError):
            self.project.retract_registration(self.user, self.justification)

        self.registration.reload()
        assert_false(self.registration.is_retracted)
        assert_is_none(self.registration.retracted_justification)
        assert_is_none(self.registration.retracted_by)
        assert_is_none(self.registration.retraction_date)


class RegistrationRetractionViewsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionViewsTestCase, self).setUp()
        self.admin_user = AuthUserFactory()
        self.admin_user.save()
        self.auth = self.admin_user.auth
        self.project = ProjectFactory(is_public=False, creator=self.admin_user)
        self.registration = RegistrationFactory(project=self.project)
        self.registration.is_public = True
        self.registration.save()

        self.retraction_url = self.registration.api_url_for('node_registration_retraction')
        self.justification = 'I loathe openness...'

    def test_retract_private_registration_raises_400(self):
        self.registration.is_public = False
        self.registration.save()

        res = self.app.post_json(
            self.retraction_url,
             auth=self.auth,
             expect_errors=True,
        )

        assert_equal(res.status_code, 400)
        self.registration.reload()
        assert_false(self.registration.is_retracted)
        assert_is_none(self.registration.retracted_justification)

    def test_non_admin_retract_raises_401(self):
        res = self.app.post_json(self.retraction_url, expect_errors=True)

        assert_equals(res.status_code, 401)
        self.registration.reload()
        assert_false(self.registration.is_retracted)
        assert_is_none(self.registration.retracted_justification)

    def test_retract_without_justification_raises_200(self):
        res = self.app.post_json(
            self.retraction_url,
             {'justification': ''},
             auth=self.auth,
        )

        assert_equal(res.status_code, 200)
        self.registration.reload()
        assert_true(self.registration.is_retracted)
        assert_equal(self.registration.retracted_justification, u'')

    def test_redirect_if_retracted(self):
        expected_redirect_url = self.registration.web_url_for('view_project')
        res = self.app.post_json(
            self.retraction_url,
             {'justification': self.justification},
             auth=self.auth,
             expect_errors=True,
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], expected_redirect_url)
        self.registration.reload()
        assert_true(self.registration.is_retracted)
        assert_equal(self.registration.retracted_justification, self.justification)

    def test_cant_access_non_approved_resource(self):
        # Retract public registration
        expected_redirect_url = self.registration.web_url_for('view_project')
        res = self.app.post_json(
            self.retraction_url,
             {'justification': self.justification},
             auth=self.auth,
             expect_errors=True,
        )
        # Verify it's accessible
        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], expected_redirect_url)
        self.registration.reload()
        assert_true(self.registration.is_retracted)
        # Ensure access to resources not explicitly granting permission to retractions returns 400
        res = self.app.get(
            self.registration.web_url_for('project_wiki_home'),
            expect_errors=True
        )
        assert_equal(res.status_code, 400)


class RegistrationRetractionSearchTestCase(OsfTestCase):

    def test_retract_wiki_not_in_search(self):
        pass

    def test_retract_search_indicator_in_results(self):
        pass


@must_be_valid_project
def valid_project_helper(**kwargs):
    return kwargs

@must_be_valid_project(are_retractions_valid=True)
def as_factory_allow_retractions(**kwargs):
    return kwargs


class TestValidProject(OsfTestCase):

    def setUp(self):
        super(TestValidProject, self).setUp()
        self.project = ProjectFactory()
        self.node = NodeFactory(project=self.project)

    def test_populates_kwargs_project(self):
        res = valid_project_helper(pid=self.project._id)
        assert_equal(res['project'], self.project)
        assert_is_none(res['node'])

    def test_populates_kwargs_node(self):
        res = valid_project_helper(pid=self.project._id, nid=self.node._id)
        assert_equal(res['project'], self.project)
        assert_equal(res['node'], self.node)

    def test_project_not_found(self):
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid='fakepid')
        assert_equal(exc_info.exception.code, 404)

    def test_project_category_mismatch(self):
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.node._id)
        assert_equal(exc_info.exception.code, 400)

    def test_project_deleted(self):
        self.project.is_deleted = True
        self.project.save()
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id)
        assert_equal(exc_info.exception.code, 410)

    def test_node_not_found(self):
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid='fakenid')
        assert_equal(exc_info.exception.code, 404)

    def test_node_deleted(self):
        self.node.is_deleted = True
        self.node.save()
        with assert_raises(HTTPError) as exc_info:
            valid_project_helper(pid=self.project._id, nid=self.node._id)
        assert_equal(exc_info.exception.code, 410)

    def test_valid_project_as_factory_allow_retractions_is_retracted(self):
        self.project.is_registration = True
        self.project.is_retracted = True
        self.project.save()
        res = as_factory_allow_retractions(pid=self.project._id)
        assert_equal(res['project'], self.project)
