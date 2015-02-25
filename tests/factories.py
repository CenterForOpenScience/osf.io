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
import datetime
from factory import base, Sequence, SubFactory, post_generation, LazyAttribute

from framework.mongo import StoredObject
from framework.auth import User, Auth
from framework.auth.utils import impute_names_model
from website.oauth.models import ExternalAccount
from website.project.model import (
    ApiKey, Node, NodeLog, WatchConfig, Tag, Pointer, Comment, PrivateLink,
)

from website.addons.wiki.model import NodeWikiPage
from tests.base import fake


# TODO: This is a hack. Check whether FactoryBoy can do this better
def save_kwargs(**kwargs):
    for value in kwargs.itervalues():
        if isinstance(value, StoredObject) and not value._is_loaded:
            value.save()


def FakerAttribute(provider, **kwargs):
    """Attribute that lazily generates a value using the Faker library.
    Example: ::

        class UserFactory(ModularOdmFactory):
            name = FakerAttribute('name')
    """
    fake_gen = getattr(fake, provider)
    if not fake_gen:
        raise ValueError('{0!r} is not a valid faker provider.'.format(provider))
    return LazyAttribute(lambda x: fake_gen(**kwargs))


class ModularOdmFactory(base.Factory):
    """Base factory for modular-odm objects.
    """

    ABSTRACT_FACTORY = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        """Build an object without saving it."""
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
    date_confirmed = datetime.datetime(2014, 2, 21)

    @post_generation
    def set_names(self, create, extracted):
        parsed = impute_names_model(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()


class AuthUserFactory(UserFactory):
    """A user that automatically has an api key, for quick authentication.

    Example: ::
        user = AuthUserFactory()
        res = self.app.get(url, auth=user.auth)  # user is "logged in"
    """

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


class PrivateLinkFactory(ModularOdmFactory):
    FACTORY_FOR = PrivateLink

    name = "link"
    key = "foobarblaz"
    anonymous = False
    creator = SubFactory(AuthUserFactory)

class AbstractNodeFactory(ModularOdmFactory):
    FACTORY_FOR = Node

    title = 'The meaning of life'
    description = 'The meaning of life is 42.'
    creator = SubFactory(AuthUserFactory)


class ProjectFactory(AbstractNodeFactory):
    category = 'project'


class FolderFactory(ProjectFactory):
    is_folder = True


class DashboardFactory(FolderFactory):
    is_dashboard = True


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
        #schema = schema or MetaSchema.find_one(
        #    Q('name', 'eq', 'Open-Ended_Registration')
        #)
        schema = None
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


class NodeWikiFactory(ModularOdmFactory):
    FACTORY_FOR = NodeWikiPage

    page_name = 'home'
    content = 'Some content'
    version = 1
    user = SubFactory(UserFactory)
    node = SubFactory(NodeFactory)


class UnregUserFactory(ModularOdmFactory):
    """Factory for an unregistered user. Uses User.create_unregistered()
    to create an instance.

    """
    FACTORY_FOR = User
    email = Sequence(lambda n: "brian{0}@queen.com".format(n))
    fullname = Sequence(lambda n: "Brian May{0}".format(n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        '''Build an object without saving it.'''
        return target_class.create_unregistered(*args, **kwargs)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        instance = target_class.create_unregistered(*args, **kwargs)
        instance.save()
        return instance

class UnconfirmedUserFactory(ModularOdmFactory):
    """Factory for a user that has not yet confirmed their primary email
    address (username).
    """

    FACTORY_FOR = User
    username = Sequence(lambda n: 'roger{0}@queen.com'.format(n))
    fullname = Sequence(lambda n: 'Roger Taylor{0}'.format(n))
    password = 'killerqueen'

    @classmethod
    def _build(cls, target_class, username, password, fullname):
        '''Build an object without saving it.'''
        return target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )

    @classmethod
    def _create(cls, target_class, username, password, fullname):
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.save()
        return instance


class AuthFactory(base.Factory):
    FACTORY_FOR = Auth
    user = SubFactory(UserFactory)
    api_key = SubFactory(ApiKeyFactory)


class ProjectWithAddonFactory(ProjectFactory):
    """Factory for a project that has an addon. The addon will be added to
    both the Node and the creator records. ::

        p = ProjectWithAddonFactory(addon='github')
        p.get_addon('github') # => github node settings object
        p.creator.get_addon('github') # => github user settings object

    """

    # TODO: Should use mock addon objects
    @classmethod
    def _build(cls, target_class, addon='s3', *args, **kwargs):
        '''Build an object without saving it.'''
        instance = ProjectFactory._build(target_class, *args, **kwargs)
        auth = Auth(user=instance.creator)
        instance.add_addon(addon, auth)
        instance.creator.add_addon(addon)
        return instance

    @classmethod
    def _create(cls, target_class, addon='s3', *args, **kwargs):
        instance = ProjectFactory._create(target_class, *args, **kwargs)
        auth = Auth(user=instance.creator)
        instance.add_addon(addon, auth)
        instance.creator.add_addon(addon)
        instance.save()
        return instance

# Deprecated unregistered user factory, used mainly for testing migration

class DeprecatedUnregUser(object):
    '''A dummy "model" for an unregistered user.'''
    def __init__(self, nr_name, nr_email):
        self.nr_name = nr_name
        self.nr_email = nr_email

    def to_dict(self):
        return {"nr_name": self.nr_name, "nr_email": self.nr_email}


class DeprecatedUnregUserFactory(base.Factory):
    """Generates a dictonary represenation of an unregistered user, in the
    format expected by the OSF.
    ::

        >>> from tests.factories import UnregUserFactory
        >>> UnregUserFactory()
        {'nr_name': 'Tom Jones0', 'nr_email': 'tom0@example.com'}
        >>> UnregUserFactory()
        {'nr_name': 'Tom Jones1', 'nr_email': 'tom1@example.com'}
    """
    FACTORY_FOR = DeprecatedUnregUser

    nr_name = Sequence(lambda n: "Tom Jones{0}".format(n))
    nr_email = Sequence(lambda n: "tom{0}@example.com".format(n))

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return target_class(*args, **kwargs).to_dict()

    _build = _create


class CommentFactory(ModularOdmFactory):

    FACTORY_FOR = Comment
    content = Sequence(lambda n: 'Comment {0}'.format(n))
    is_public = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or node
        instance = target_class(
            node=node,
            user=user,
            target=target,
            *args, **kwargs
        )
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or node
        instance = target_class(
            node=node,
            user=user,
            target=target,
            *args, **kwargs
        )
        instance.save()
        return instance


class ExternalAccountFactory(ModularOdmFactory):
    FACTORY_FOR = ExternalAccount

    provider = 'fakeprovider'
    provider_id = Sequence(lambda n: 'user-{0}'.format(n))