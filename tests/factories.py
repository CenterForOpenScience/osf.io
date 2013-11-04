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

from factory import base, Sequence, SubFactory, PostGenerationMethodCall, post_generation

from framework.auth import User
from website.project.model import (ApiKey, Node, NodeLog, WatchConfig,
                                   MetaData, Tag)

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
    # Sets the password upon generation but before saving
    password = PostGenerationMethodCall("set_password", "defaultpassword")
    fullname = Sequence(lambda n: "Freddie Mercury{0}".format(n))
    is_registered = True
    is_claimed = True
    api_keys = []


class TagFactory(ModularOdmFactory):
    FACTORY_FOR = Tag

    _id = Sequence(lambda n: "scientastic-{}".format(n))


class ApiKeyFactory(ModularOdmFactory):
    FACTORY_FOR = ApiKey


class NodeFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    category = 'hypothesis'
    title = 'The meaning of life'
    description = "The meaning of life is 42."
    is_public = False
    is_registration = False


class ProjectFactory(NodeFactory):
    FACTORY_FOR = Node
    category = 'project'
    creator = SubFactory(UserFactory)

    @post_generation
    def add_created_log(self, create, extracted):
        '''Add a log after creating a new project.'''
        self.add_log('project_created',
            params={
                'project': self._primary_key,
            },
            user=self.creator,
            log_date=self.date_created
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
