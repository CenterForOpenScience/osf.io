# -*- coding: utf-8 -*-
import functools
import datetime as dt

import factory
from factory.django import DjangoModelFactory
from faker import Factory
from modularodm.exceptions import NoResultsFound

from website.project.licenses import ensure_licenses

from osf_models import models
from osf_models.utils.names import impute_names_model
from osf_models.modm_compat import Q

fake = Factory.create()
ensure_licenses = functools.partial(ensure_licenses, warn=False)


def FakeList(provider, n, *args, **kwargs):
    func = getattr(fake, provider)
    return [func(*args, **kwargs) for _ in range(n)]

class UserFactory(DjangoModelFactory):
    username = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password',
                                                'queenfan86')
    is_registered = True
    is_claimed = True
    date_confirmed = factory.Faker('date_time')
    merged_by = None
    verification_key = None

    class Meta:
        model = models.OSFUser

    @factory.post_generation
    def set_names(self, create, extracted):
        parsed = impute_names_model(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()

    @factory.post_generation
    def set_emails(self, create, extracted):
        if self.username not in self.emails:
            self.emails.append(str(self.username))

class UnregUserFactory(DjangoModelFactory):
    email = factory.Faker('email')
    fullname = factory.Faker('name')
    date_confirmed = factory.Faker('date_time')
    date_registered = factory.Faker('date_time')

    class Meta:
        model = models.OSFUser

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        ret = target_class.create_unregistered(email=kwargs.pop('email'), fullname=kwargs.pop('fullname'))
        for key, val in kwargs.items():
            setattr(ret, key, val)
        return ret

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        ret = target_class.create_unregistered(email=kwargs.pop('email'), fullname=kwargs.pop('fullname'))
        for key, val in kwargs.items():
            setattr(ret, key, val)
        ret.save()
        return ret


class UnconfirmedUserFactory(DjangoModelFactory):
    """Factory for a user that has not yet confirmed their primary email
    address (username).
    """
    class Meta:
        model = models.OSFUser
    username = factory.Faker('email')
    fullname = factory.Faker('name')
    password = 'lolomglgt'

    @classmethod
    def _build(cls, target_class, username, password, fullname):
        '''Build an object without saving it.'''
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time()
        return instance

    @classmethod
    def _create(cls, target_class, username, password, fullname):
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time()

        instance.save()
        return instance


class NodeFactory(DjangoModelFactory):
    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    date_created = factory.LazyFunction(dt.datetime.now)
    creator = factory.SubFactory(UserFactory)

    class Meta:
        model = models.Node

class InstitutionFactory(DjangoModelFactory):
    name = factory.Faker('company')
    auth_url = factory.Faker('url')
    logout_url = factory.Faker('url')
    domains = FakeList('url', n=3)
    email_domains = FakeList('domain_name', n=1)
    logo_name = factory.Faker('file_name')

    class Meta:
        model = models.Institution

class NodeLicenseRecordFactory(DjangoModelFactory):
    year = factory.Faker('year')
    copyright_holders = FakeList('name', n=3)

    class Meta:
        model = models.NodeLicenseRecord

    @classmethod
    def _create(cls, *args, **kwargs):
        try:
            models.NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        except NoResultsFound:
            ensure_licenses()
        kwargs['node_license'] = kwargs.get(
            'node_license',
            models.NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        )
        return super(NodeLicenseRecordFactory, cls)._create(*args, **kwargs)
