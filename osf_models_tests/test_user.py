# -*- coding: utf-8 -*-
import datetime as dt

from modularodm.exceptions import ValidationError
import mock
import pytest

from osf_models.models.user import OSFUser as User
from osf_models.utils.names import impute_names_model

from .factories import fake, UserFactory

@pytest.mark.django_db
def test_factory():
    user = UserFactory.build()
    user.save()

# Tests copied from tests/test_models.py
@pytest.mark.django_db
class TestOSFUser:

    def test_create(self):
        name, email = fake.name(), fake.email()
        user = User.create(
            username=email, password='foobar', fullname=name
        )
        # TODO: Remove me when auto_now_add is enabled (post-migration)
        user.date_registered = dt.datetime.utcnow()
        user.save()
        assert user.check_password('foobar') is True
        assert user._id
        assert user.given_name == impute_names_model(name)['given_name']

    def test_create_unconfirmed(self):
        name, email = fake.name(), fake.email()
        user = User.create_unconfirmed(
            username=email, password='foobar', fullname=name
        )
        # TODO: Remove me when auto_now_add is enabled (post-migration)
        user.date_registered = dt.datetime.utcnow()
        user.save()
        assert user.is_registered is False
        assert len(user.email_verifications.keys()) == 1
        assert len(user.emails) == 0, 'primary email has not been added to emails list'

    def test_update_guessed_names(self):
        name = fake.name()
        u = User(fullname=name)
        u.update_guessed_names()

        parsed = impute_names_model(name)
        assert u.fullname == name
        assert u.given_name == parsed['given_name']
        assert u.middle_names == parsed['middle_names']
        assert u.family_name == parsed['family_name']
        assert u.suffix == parsed['suffix']


@pytest.mark.django_db
class TestAddUnconfirmedEmail:

    @mock.patch('osf_models.utils.security.random_string')
    def test_add_unconfirmed_email(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        assert len(u.email_verifications.keys()) == 0
        u.add_unconfirmed_email('foo@bar.com')
        assert len(u.email_verifications.keys()) == 1
        assert u.email_verifications[token]['email'] == 'foo@bar.com'

    @mock.patch('osf_models.utils.security.random_string')
    def test_add_unconfirmed_email_adds_expiration_date(self, random_string):
        token = fake.lexify('???????')
        random_string.return_value = token
        u = UserFactory()
        u.add_unconfirmed_email('test@osf.io')
        assert isinstance(u.email_verifications[token]['expiration'], dt.datetime)

    def test_add_blank_unconfirmed_email(self):
        user = UserFactory()
        with pytest.raises(ValidationError) as exc_info:
            user.add_unconfirmed_email('')
        assert exc_info.value.message == 'Enter a valid email address.'
