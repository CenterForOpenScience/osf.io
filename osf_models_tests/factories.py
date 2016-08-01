# -*- coding: utf-8 -*-
import datetime as dt

import factory
from factory.django import DjangoModelFactory
from faker import Factory

from osf_models import models
from osf_models.utils.names import impute_names_model

fake = Factory.create()


def FakeList(provider, n, *args, **kwargs):
    func = getattr(fake, provider)
    return [func(*args, **kwargs) for _ in range(n)]

class NodeFactory(DjangoModelFactory):
    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    date_created = factory.LazyFunction(dt.datetime.now)
    class Meta:
        model = models.Node


class InstitutionFactory(DjangoModelFactory):
    name = factory.Faker('company')
    domains = FakeList('domain_name', n=2)
    email_domains = FakeList('domain_name', n=2)

    class Meta:
        model = models.Institution


class UserFactory(DjangoModelFactory):
    username = factory.Faker('email')
    password = 'password'
    is_registered = True
    is_claimed = True
    date_confirmed = factory.Faker('date_time')
    date_registered = factory.Faker('date_time')
    merged_by = None
    email_verifications = {}
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
