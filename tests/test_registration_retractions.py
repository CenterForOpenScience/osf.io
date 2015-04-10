"""Tests related to retraction of public registrations"""

import datetime
from nose.tools import *  # noqa
from faker import Factory

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, RegistrationFactory, UserFactory, AuthUserFactory

from modularodm.exceptions import ValidationTypeError, ValidationValueError
from website.exceptions import NodeStateError

from framework.auth.core import Auth


fake = Factory.create()


class RegistrationRetractionModelsTestCase(OsfTestCase):
    def setUp(self):
        super(RegistrationRetractionModelsTestCase, self).setUp()
        self.user = UserFactory()
        self.consolidate_auth = Auth(user=self.user)
        self.project = ProjectFactory(creator=self.user)
        self.registration = RegistrationFactory(project=self.project)
        self.valid_justification = fake.sentence()
        self.invalid_justification = fake.text(max_nb_chars=3000)

    def test_retract(self):
        self.registration.is_public = True
        self.registration.retract_registration(self.user, self.valid_justification)
        self.registration.save()

        self.registration.reload()
        assert_true(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.justification, self.valid_justification)
        assert_equal(self.registration.retraction.by, self.user)
        assert_equal(
            self.registration.retraction.date.date(),
            datetime.datetime.utcnow().date()
        )

    def test_long_justification_raises_validation_value_error(self):
        self.registration.is_public = True
        self.registration.save()
        with assert_raises(ValidationValueError):
            self.registration.retract_registration(self.user, self.invalid_justification)
            self.registration.save()
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_private_registration_throws_type_error(self):
        with assert_raises(NodeStateError):
            self.registration.retract_registration(self.user, self.valid_justification)
            self.registration.save()

        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_public_non_registration_throws_type_error(self):
        self.project.is_public = True
        self.project.save()
        with assert_raises(NodeStateError):
            self.project.retract_registration(self.user, self.valid_justification)

        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_set_public_registration_to_private_raises_node_exception(self):
        self.registration.is_public = True
        self.registration.save()
        with assert_raises(NodeStateError):
            self.registration.set_privacy('private')

        self.registration.reload()
        assert_true(self.registration.is_public)


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

        self.retraction_post_url = self.registration.api_url_for('node_registration_retraction_post')
        self.justification = fake.sentence()

    def test_retract_private_registration_raises_400(self):
        self.registration.is_public = False
        self.registration.save()

        res = self.app.post_json(
            self.retraction_post_url,
             auth=self.auth,
             expect_errors=True,
        )

        assert_equal(res.status_code, 400)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_non_admin_retract_raises_401(self):
        res = self.app.post_json(self.retraction_post_url, expect_errors=True)

        assert_equals(res.status_code, 401)
        self.registration.reload()
        assert_is_none(self.registration.retraction)

    def test_retract_without_justification_raises_200(self):
        res = self.app.post_json(
            self.retraction_post_url,
             {'justification': ''},
             auth=self.auth,
        )

        assert_equal(res.status_code, 200)
        self.registration.reload()
        assert_true(self.registration.retraction.is_retracted)
        assert_is_none(self.registration.retraction.justification)

    def test_redirect_if_retracted(self):
        expected_redirect_url = self.registration.web_url_for('view_project')
        res = self.app.post_json(
            self.retraction_post_url,
             {'justification': self.justification},
             auth=self.auth,
             expect_errors=True,
        )

        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], expected_redirect_url)
        self.registration.reload()
        assert_true(self.registration.retraction.is_retracted)
        assert_equal(self.registration.retraction.justification, self.justification)

    def test_cant_access_non_approved_resource(self):
        # Retract public registration
        expected_redirect_url = self.registration.web_url_for('view_project')
        res = self.app.post_json(
            self.retraction_post_url,
             {'justification': self.justification},
             auth=self.auth,
             expect_errors=True,
        )
        # Verify it's accessible
        assert_equal(res.status_code, 200)
        assert_equal(res.json['redirectUrl'], expected_redirect_url)
        self.registration.reload()
        assert_true(self.registration.retraction.is_retracted)
        # Ensure access to resources not explicitly granting permission to retractions returns 400
        res = self.app.get(
            self.registration.web_url_for('project_wiki_home'),
            expect_errors=True
        )
        assert_equal(res.status_code, 400)
