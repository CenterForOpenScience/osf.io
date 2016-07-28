# -*- coding: utf-8 -*-
import datetime as dt

import factory
from factory.django import DjangoModelFactory
from osf_models.models.node import Node


class NodeFactory(DjangoModelFactory):
    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    date_created = factory.LazyFunction(dt.datetime.now)
    class Meta:
        model = Node
