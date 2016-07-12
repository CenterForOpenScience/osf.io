# -*- coding: utf-8 -*-

from nose.tools import *  # PEP8 asserts

from modularodm.exceptions import ValidationError

from tests.base import OsfTestCase
from tests.factories import ProjectFactory, RegistrationFactory
from website.addons.forward.tests.factories import ForwardSettingsFactory


class TestNodeSettings(OsfTestCase):

    def setUp(self):
        super(TestNodeSettings, self).setUp()
        self.node = ProjectFactory()
        self.settings = ForwardSettingsFactory(owner=self.node)
        self.node.save()

    def test_forward_registered(self):
        registration = RegistrationFactory(project=self.node)
        assert registration.has_addon('forward')
        
        forward = registration.get_addon('forward')
        assert_equal(forward.url, 'http://frozen.pizza.reviews/')

class TestSettingsValidation(OsfTestCase):

    def setUp(self):
        super(TestSettingsValidation, self).setUp()
        self.settings = ForwardSettingsFactory()

    def test_validate_url_bad(self):
        self.settings.url = 'badurl'
        with assert_raises(ValidationError):
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
        with assert_raises(ValidationError):
            self.settings.save()
