# -*- coding: utf-8 -*-
"""Factories for the OSF models, including an abstract ModularOdmFactory.

Example usage: ::

    >>> from tests.factories import UserFactory
    >>> user1 = UserFactory()
    >>> user1.username
    fred0@example.com
    >>> user2 = UserFactory()
    fred1@example.com

Factory boy docs: http://factoryboy.readthedocs.org/

"""
import datetime as dt

from factory import base, Sequence, SubFactory, post_generation

from framework import StoredObject
from framework.auth import User, Q
from framework.auth.decorators import Auth
from framework.auth.utils import parse_name
from website.project.model import (
    ApiKey, Node, NodeLog, WatchConfig, MetaData, Tag, MetaSchema, Pointer,
)

from website.addons.wiki.model import NodeWikiPage


# TODO: This is a hack. Check whether FactoryBoy can do this better
def save_kwargs(**kwargs):
    for value in kwargs.itervalues():
        if isinstance(value, StoredObject) and not value._is_loaded:
            value.save()


class ModularOdmFactory(base.Factory):

    """Base factory for modular-odm objects.
    """

    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        save_kwargs(**kwargs)
        return target_class(*args, **kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        save_kwargs(**kwargs)
        instance = target_class(*args, **kwargs)
        instance.save()
        return instance


class UserFactory(ModularOdmFactory):
    FACTORY_FOR = User

    username = Sequence(lambda n: "fred{0}@example.com".format(n))
    # Don't use post generation call to set_password because
    # It slows down the tests dramatically
    password = "password"
    fullname = Sequence(lambda n: "Freddie Mercury{0}".format(n))
    is_registered = True
    is_claimed = True
    api_keys = []

    @post_generation
    def set_date_registered(self, create, extracted):
        self.date_registered = dt.datetime.utcnow()
        if create:
            self.save()

    @post_generation
    def set_names(self, create, extracted):
        parsed = parse_name(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()


class AuthUserFactory(UserFactory):

    @post_generation
    def add_api_key(self, create, extracted):
        key = ApiKeyFactory()
        self.api_keys.append(key)
        self.save()
        self.auth = ('test', key._primary_key)


class TagFactory(ModularOdmFactory):
    FACTORY_FOR = Tag

    _id = Sequence(lambda n: "scientastic-{}".format(n))


class ApiKeyFactory(ModularOdmFactory):
    FACTORY_FOR = ApiKey


class AbstractNodeFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    title = 'The meaning of life'
    description = 'The meaning of life is 42.'
    creator = SubFactory(UserFactory)


class ProjectFactory(AbstractNodeFactory):
    category = 'project'


class NodeFactory(AbstractNodeFactory):
    category = 'hypothesis'
    project = SubFactory(ProjectFactory)


class RegistrationFactory(AbstractNodeFactory):

    # Default project is created if not provided
    category = 'project'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise Exception("Cannot build registration without saving.")

    @classmethod
    def _create(cls, target_class, project=None, schema=None, user=None,
                template=None, data=None, *args, **kwargs):

        save_kwargs(**kwargs)

        # Original project to be registered
        project = project or target_class(*args, **kwargs)
        project.save()

        # Default registration parameters
        schema = schema or MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended_Registration')
        )
        user = user or project.creator
        template = template or "Template1"
        data = data or "Some words"
        auth = Auth(user=user)
        return project.register_node(
            schema=schema,
            auth=auth,
            template=template,
            data=data,
        )


class PointerFactory(ModularOdmFactory):
    FACTORY_FOR = Pointer
    node = SubFactory(NodeFactory)


class NodeLogFactory(ModularOdmFactory):
    FACTORY_FOR = NodeLog
    action = 'file_added'
    user = SubFactory(UserFactory)


class WatchConfigFactory(ModularOdmFactory):
    FACTORY_FOR = WatchConfig
    node = SubFactory(NodeFactory)


class MetaDataFactory(ModularOdmFactory):
    FACTORY_FOR = MetaData


class NodeWikiFactory(ModularOdmFactory):
    FACTORY_FOR = NodeWikiPage

    page_name = 'home'
    content = 'Some content'
    version = 1
    user = SubFactory(UserFactory)
    node = SubFactory(NodeFactory)


class UnregUser(object):
    '''A dummy "model" for an unregistered user.'''
    def __init__(self, nr_name, nr_email):
        self.nr_name = nr_name
        self.nr_email = nr_email

    def to_dict(self):
        return {"nr_name": self.nr_name, "nr_email": self.nr_email}


class UnregUserFactory(base.Factory):
    """Generates a dictonary represenation of an unregistered user, in the
    format expected by the OSF.
    ::

        >>> from tests.factories import UnregUserFactory
        >>> UnregUserFactory()
        {'nr_name': 'Tom Jones0', 'nr_email': 'tom0@example.com'}
        >>> UnregUserFactory()
        {'nr_name': 'Tom Jones1', 'nr_email': 'tom1@example.com'}
    """
    FACTORY_FOR = UnregUser

    nr_name = Sequence(lambda n: "Tom Jones{0}".format(n))
    nr_email = Sequence(lambda n: "tom{0}@example.com".format(n))

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return target_class(*args, **kwargs).to_dict()

    _build = _create
