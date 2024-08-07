import unittest
import pytest

from django.core.exceptions import ValidationError

from osf_tests.factories import ProjectFactory, RegistrationFactory
from addons.forward.tests.factories import ForwardSettingsFactory

pytestmark = pytest.mark.django_db


class TestNodeSettings(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.node = ProjectFactory()
        self.settings = ForwardSettingsFactory(owner=self.node)
        self.node.save()

    def test_forward_registered(self):
        registration = RegistrationFactory(project=self.node)
        assert registration.has_addon('forward')

        forward = registration.get_addon('forward')
        assert forward.url == 'http://frozen.pizza.reviews/'

@pytest.mark.enable_implicit_clean
class TestSettingsValidation(unittest.TestCase):

    def setUp(self):
        super().setUp()
        self.settings = ForwardSettingsFactory()

    def test_validate_url_bad(self):
        self.settings.url = 'badurl'
        with pytest.raises(ValidationError):
            self.settings.save()

    def test_validate_url_good(self):
        self.settings.url = 'http://frozen.pizza.reviews/'
        try:
            self.settings.save()
        except ValidationError:
            assert 0

    def test_label_sanitary(self):
        self.settings.label = 'safe'
        try:
            self.settings.save()
        except ValidationError:
            assert False

    def test_label_unsanitary(self):
        self.settings.label = 'un<br />safe'
        with pytest.raises(ValidationError):
            self.settings.save()
