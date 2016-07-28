# -*- coding: utf-8 -*-
import datetime as dt

import factory
from factory.django import DjangoModelFactory
from faker import Factory

from osf_models import models


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
