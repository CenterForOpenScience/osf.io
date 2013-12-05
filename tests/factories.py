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

from factory import base, Sequence, SubFactory, PostGenerationMethodCall, post_generation

from framework.auth import User, Q
from website.project.model import (ApiKey, Node, NodeLog, WatchConfig,
                                   MetaData, Tag, NodeWikiPage, MetaSchema)

class ModularOdmFactory(base.Factory):

    """Base factory for modular-odm objects.
    """

    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        return target_class(*args, **kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
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


class TagFactory(ModularOdmFactory):
    FACTORY_FOR = Tag

    _id = Sequence(lambda n: "scientastic-{}".format(n))


class ApiKeyFactory(ModularOdmFactory):
    FACTORY_FOR = ApiKey


class ProjectFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    category = 'project'
    title = 'My Little Project'
    description = 'My little description'
    creator = SubFactory(UserFactory)


class NodeFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    category = 'hypothesis'
    title = 'The meaning of life'
    description = "The meaning of life is 42."
    creator = SubFactory(UserFactory)
    project = SubFactory(ProjectFactory)


class RegistrationFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    # Arguments given to the original project
    category = 'project'
    title = "Original Project"
    description = "This is the default."
    creator = SubFactory(UserFactory)

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        raise Exception("Cannot build registration without saving.")

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        parent = kwargs.get('project') or target_class(*args, **kwargs)
        schema = kwargs.get('schema') or MetaSchema.find_one(
            Q('name', 'eq', 'Open-Ended_Registration')
        )
        user = kwargs.get('user') or kwargs['creator']
        template = kwargs.get('template') or "Template1"
        data = kwargs.get('data') or "Some words"
        return parent.register_node(
            schema=schema,
            user=user,
            template=template,
            data=data,
        )

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

