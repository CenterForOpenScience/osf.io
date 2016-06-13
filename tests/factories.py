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
import mock
import datetime
import functools
from factory import base, Sequence, SubFactory, post_generation, LazyAttribute

from mock import patch, Mock
from modularodm import Q
from modularodm.exceptions import NoResultsFound

from framework.mongo import StoredObject
from framework.auth import User, Auth
from framework.auth.utils import impute_names_model, impute_names
from framework.guid.model import Guid
from framework.sessions.model import Session
from website import security
from website.addons import base as addons_base
from website.files.models import StoredFileNode
from website.oauth.models import (
    ApiOAuth2Application,
    ApiOAuth2PersonalToken,
    ExternalAccount,
    ExternalProvider
)
from website.project.model import (
    Comment, DraftRegistration, MetaSchema, Node, NodeLog, Pointer,
    PrivateLink, Tag, WatchConfig, AlternativeCitation,
    ensure_schemas, Institution
)
from website.project.sanctions import (
    Embargo,
    EmbargoTerminationApproval,
    RegistrationApproval,
    Retraction,
    Sanction,
)
from website.notifications.model import NotificationSubscription, NotificationDigest
from website.archiver.model import ArchiveTarget, ArchiveJob
from website.identifiers.model import Identifier
from website.archiver import ARCHIVER_SUCCESS
from website.project.licenses import NodeLicense, NodeLicenseRecord, ensure_licenses
ensure_licenses = functools.partial(ensure_licenses, warn=False)

from website.addons.wiki.model import NodeWikiPage
from website.util import permissions

from tests.base import fake
from tests.base import get_default_metaschema

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
    class Meta:
        abstract = True

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
    class Meta:
        model = User
        abstract = False

    username = Sequence(lambda n: "fred{0}@example.com".format(n))
    # Don't use post generation call to set_password because
    # It slows down the tests dramatically
    password = "password"
    fullname = Sequence(lambda n: "Freddie Mercury{0}".format(n))
    is_registered = True
    is_claimed = True
    date_confirmed = datetime.datetime(2014, 2, 21)
    merged_by = None
    email_verifications = {}
    verification_key = None

    @post_generation
    def set_names(self, create, extracted):
        parsed = impute_names_model(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()

    @post_generation
    def set_emails(self, create, extracted):
        if self.username not in self.emails:
            self.emails.append(self.username)
            self.save()


class AuthUserFactory(UserFactory):
    """A user that automatically has an api key, for quick authentication.

    Example: ::
        user = AuthUserFactory()
        res = self.app.get(url, auth=user.auth)  # user is "logged in"
    """

    @post_generation
    def add_auth(self, create, extracted):
        self.set_password('password', notify=False)
        self.save()
        self.auth = (self.username, 'password')


class TagFactory(ModularOdmFactory):
    class Meta:
        model = Tag

    _id = Sequence(lambda n: "scientastic-{}".format(n))


class ApiOAuth2ApplicationFactory(ModularOdmFactory):
    class Meta:
        model = ApiOAuth2Application

    owner = SubFactory(UserFactory)

    name = Sequence(lambda n: 'Example OAuth2 Application #{}'.format(n))

    home_url = 'ftp://ftp.ncbi.nlm.nimh.gov/'
    callback_url = 'http://example.uk'


class ApiOAuth2PersonalTokenFactory(ModularOdmFactory):
    class Meta:
        model = ApiOAuth2PersonalToken

    owner = SubFactory(UserFactory)

    scopes = 'osf.full_write osf.full_read'

    name = Sequence(lambda n: 'Example OAuth2 Personal Token #{}'.format(n))


class PrivateLinkFactory(ModularOdmFactory):
    class Meta:
        model = PrivateLink

    name = "link"
    key = Sequence(lambda n: 'foobar{}'.format(n))
    anonymous = False
    creator = SubFactory(AuthUserFactory)


class AbstractNodeFactory(ModularOdmFactory):
    class Meta:
        model = Node

    title = 'The meaning of life'
    description = 'The meaning of life is 42.'
    creator = SubFactory(AuthUserFactory)


class ProjectFactory(AbstractNodeFactory):
    category = 'project'


class CollectionFactory(ProjectFactory):
    is_collection = True


class BookmarkCollectionFactory(CollectionFactory):
    is_bookmark_collection = True


class NodeFactory(AbstractNodeFactory):
    category = 'hypothesis'
    parent = SubFactory(ProjectFactory)


class RegistrationFactory(AbstractNodeFactory):

    creator = None
    # Default project is created if not provided
    category = 'project'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise Exception("Cannot build registration without saving.")

    @classmethod
    def _create(cls, target_class, project=None, is_public=False,
                schema=None, data=None,
                archive=False, embargo=None, registration_approval=None, retraction=None,
                *args, **kwargs):
        save_kwargs(**kwargs)
        user = None
        if project:
            user = project.creator
        user = kwargs.get('user') or kwargs.get('creator') or user or UserFactory()
        kwargs['creator'] = user
        # Original project to be registered
        project = project or target_class(*args, **kwargs)
        if user._id not in project.permissions:
            project.add_contributor(
                contributor=user,
                permissions=permissions.CREATOR_PERMISSIONS,
                log=False,
                save=False
            )
        project.save()

        # Default registration parameters
        schema = schema or get_default_metaschema()
        data = data or {'some': 'data'}
        auth = Auth(user=user)
        register = lambda: project.register_node(
            schema=schema,
            auth=auth,
            data=data
        )

        def add_approval_step(reg):
            if embargo:
                reg.embargo = embargo
            elif registration_approval:
                reg.registration_approval = registration_approval
            elif retraction:
                reg.retraction = retraction
            else:
                reg.require_approval(reg.creator)
            reg.save()
            reg.sanction.add_authorizer(reg.creator, reg)
            reg.sanction.save()

        if archive:
            reg = register()
            add_approval_step(reg)
        else:
            with patch('framework.celery_tasks.handlers.enqueue_task'):
                reg = register()
                add_approval_step(reg)
            with patch.object(reg.archive_job, 'archive_tree_finished', Mock(return_value=True)):
                reg.archive_job.status = ARCHIVER_SUCCESS
                reg.archive_job.save()
                reg.sanction.state = Sanction.APPROVED
                reg.sanction.save()
        ArchiveJob(
            src_node=project,
            dst_node=reg,
            initiator=user,
        )
        if is_public:
            reg.is_public = True
        reg.save()
        return reg


class WithdrawnRegistrationFactory(AbstractNodeFactory):

    @classmethod
    def _create(cls, *args, **kwargs):

        registration = kwargs.pop('registration', None)
        registration.is_public = True
        user = kwargs.pop('user', registration.creator)

        registration.retract_registration(user)
        withdrawal = registration.retraction
        token = withdrawal.approval_state.values()[0]['approval_token']
        withdrawal.approve_retraction(user, token)
        withdrawal.save()

        return withdrawal


class ForkFactory(ModularOdmFactory):
    class Meta:
        model = Node

    @classmethod
    def _create(cls, *args, **kwargs):

        project = kwargs.pop('project', None)
        user = kwargs.pop('user', project.creator)
        title = kwargs.pop('title', 'Fork of ')

        fork = project.fork_node(auth=Auth(user), title=title)
        fork.save()
        return fork


class PointerFactory(ModularOdmFactory):
    class Meta:
        model = Pointer
    node = SubFactory(NodeFactory)


class NodeLogFactory(ModularOdmFactory):
    class Meta:
        model = NodeLog
    action = 'file_added'
    user = SubFactory(UserFactory)


class WatchConfigFactory(ModularOdmFactory):
    class Meta:
        model = WatchConfig
    node = SubFactory(NodeFactory)


class SanctionFactory(ModularOdmFactory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, target_class, initiated_by=None, approve=False, *args, **kwargs):
        user = kwargs.get('user') or UserFactory()
        kwargs['initiated_by'] = initiated_by or user
        sanction = ModularOdmFactory._create(target_class, *args, **kwargs)
        reg_kwargs = {
            'creator': user,
            'user': user,
            sanction.SHORT_NAME: sanction
        }
        RegistrationFactory(**reg_kwargs)
        if not approve:
            sanction.state = Sanction.UNAPPROVED
            sanction.save()
        return sanction

class RetractionFactory(SanctionFactory):
    class Meta:
        model = Retraction
    user = SubFactory(UserFactory)

class EmbargoFactory(SanctionFactory):
    class Meta:
        model = Embargo
    user = SubFactory(UserFactory)

class RegistrationApprovalFactory(SanctionFactory):
    class Meta:
        model = RegistrationApproval
    user = SubFactory(UserFactory)

class EmbargoTerminationApprovalFactory(ModularOdmFactory):

    FACTORY_STRATEGY = base.CREATE_STRATEGY

    @classmethod
    def create(cls, registration=None, user=None, embargo=None, *args, **kwargs):
        if registration:
            if not user:
                user = registration.creator
        else:
            user = user or AuthUserFactory()
            if not embargo:
                embargo = EmbargoFactory(initiated_by=user)
                registration = embargo._get_registration()
            else:
                registration = RegistrationFactory(creator=user, user=user, embargo=embargo)
        with mock.patch('website.project.sanctions.Sanction.is_approved', mock.Mock(return_value=True)):
            with mock.patch('website.project.sanctions.TokenApprovableSanction.ask', mock.Mock()):
                approval = registration.request_embargo_termination(Auth(user))
                return approval


class NodeWikiFactory(ModularOdmFactory):
    class Meta:
        model = NodeWikiPage

    page_name = 'home'
    content = 'Some content'
    version = 1
    user = SubFactory(UserFactory)
    node = SubFactory(NodeFactory)

    @post_generation
    def set_node_keys(self, create, extracted):
        self.node.wiki_pages_current[self.page_name] = self._id
        if self.node.wiki_pages_versions.get(self.page_name, None):
            self.node.wiki_pages_versions[self.page_name].append(self._id)
        else:
            self.node.wiki_pages_versions[self.page_name] = [self._id]
        self.node.save()


class UnregUserFactory(ModularOdmFactory):
    """Factory for an unregistered user. Uses User.create_unregistered()
    to create an instance.

    """
    class Meta:
        model = User
        abstract = False
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
    class Meta:
        model = User
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
    class Meta:
        model = Auth
    user = SubFactory(UserFactory)


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
    class Meta:
        model = DeprecatedUnregUser

    nr_name = Sequence(lambda n: "Tom Jones{0}".format(n))
    nr_email = Sequence(lambda n: "tom{0}@example.com".format(n))

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        return target_class(*args, **kwargs).to_dict()

    _build = _create


class CommentFactory(ModularOdmFactory):
    class Meta:
        model = Comment
    content = Sequence(lambda n: 'Comment {0}'.format(n))
    is_public = True

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or Guid.load(node._id)
        content = kwargs.pop('content', None) or 'Test comment.'
        instance = target_class(
            node=node,
            user=user,
            target=target,
            content=content,
            *args, **kwargs
        )
        if isinstance(target.referent, target_class):
            instance.root_target = target.referent.root_target
        else:
            instance.root_target = target
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or Guid.load(node._id)
        content = kwargs.pop('content', None) or 'Test comment.'
        instance = target_class(
            node=node,
            user=user,
            target=target,
            content=content,
            *args, **kwargs
        )
        if isinstance(target.referent, target_class):
            instance.root_target = target.referent.root_target
        else:
            instance.root_target = target
        instance.save()
        return instance


class InstitutionFactory(ProjectFactory):

    def _build(cls, target_class, *args, **kwargs):
        from random import randint
        '''Build an object without saving it.'''
        inst = ProjectFactory._build(target_class, *args, **kwargs)
        inst.institution_id = str(randint(1, 20000))
        inst.institution_name = str(randint(10, 20000))
        inst.institution_logo_name = 'logo.img'
        inst.institution_auth_url = 'http://thisIsUrl.biz'
        return Institution(inst)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        from random import randint
        inst = ProjectFactory._create(target_class, *args, **kwargs)
        inst.institution_id = str(randint(1, 20000))
        inst.institution_name = str(randint(10, 20000))
        inst.institution_logo_name = 'logo.img'
        inst.institution_auth_url = 'http://thisIsUrl.biz'
        inst.save()
        return Institution(inst)


class NotificationSubscriptionFactory(ModularOdmFactory):
    class Meta:
        model = NotificationSubscription


class NotificationDigestFactory(ModularOdmFactory):
    class Meta:
        model = NotificationDigest


class ExternalAccountFactory(ModularOdmFactory):
    class Meta:
        model = ExternalAccount

    provider = 'mock2'
    provider_id = Sequence(lambda n: 'user-{0}'.format(n))
    provider_name = 'Fake Provider'
    display_name = Sequence(lambda n: 'user-{0}'.format(n))


class SessionFactory(ModularOdmFactory):
    class Meta:
        model = Session

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        user = kwargs.pop('user', None)
        instance = target_class(*args, **kwargs)

        if user:
            instance.data['auth_user_username'] = user.username
            instance.data['auth_user_id'] = user._primary_key
            instance.data['auth_user_fullname'] = user.fullname

        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        instance = cls._build(target_class, *args, **kwargs)
        instance.save()
        return instance


class MockOAuth2Provider(ExternalProvider):
    name = "Mock OAuth 2.0 Provider"
    short_name = "mock2"

    client_id = "mock2_client_id"
    client_secret = "mock2_client_secret"

    auth_url_base = "https://mock2.com/auth"
    callback_url = "https://mock2.com/callback"
    auto_refresh_url = "https://mock2.com/callback"
    refresh_time = 300

    def handle_callback(self, response):
        return {
            'provider_id': 'mock_provider_id'
        }


class MockAddonNodeSettings(addons_base.AddonNodeSettingsBase):
    pass


class MockAddonUserSettings(addons_base.AddonUserSettingsBase):
    pass


class MockAddonUserSettingsMergeable(addons_base.AddonUserSettingsBase):
    def merge(self):
        pass


class MockOAuthAddonUserSettings(addons_base.AddonOAuthUserSettingsBase):
    oauth_provider = MockOAuth2Provider


class MockOAuthAddonNodeSettings(addons_base.AddonOAuthNodeSettingsBase):
    oauth_provider = MockOAuth2Provider

    folder_id = 'foo'
    folder_name = 'Foo'
    folder_path = '/Foo'



class ArchiveTargetFactory(ModularOdmFactory):
    class Meta:
        model = ArchiveTarget


class ArchiveJobFactory(ModularOdmFactory):
    class Meta:
        model = ArchiveJob

class AlternativeCitationFactory(ModularOdmFactory):
    class Meta:
        model = AlternativeCitation

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        name = kwargs.get('name')
        text = kwargs.get('text')
        instance = target_class(
            name=name,
            text=text
        )
        instance.save()
        return instance

class DraftRegistrationFactory(ModularOdmFactory):
    class Meta:
        model = DraftRegistration

    @classmethod
    def _create(cls, *args, **kwargs):
        branched_from = kwargs.get('branched_from')
        initiator = kwargs.get('initiator')
        registration_schema = kwargs.get('registration_schema')
        registration_metadata = kwargs.get('registration_metadata')
        if not branched_from:
            project_params = {}
            if initiator:
                project_params['creator'] = initiator
            branched_from = ProjectFactory(**project_params)
        initiator = branched_from.creator
        try:
            registration_schema = registration_schema or MetaSchema.find()[0]
        except IndexError:
            ensure_schemas()
        registration_metadata = registration_metadata or {}
        draft = DraftRegistration.create_from_node(
            branched_from,
            user=initiator,
            schema=registration_schema,
            data=registration_metadata,
        )
        return draft

class NodeLicenseRecordFactory(ModularOdmFactory):
    class Meta:
        model = NodeLicenseRecord

    @classmethod
    def _create(cls, *args, **kwargs):
        try:
            NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        except NoResultsFound:
            ensure_licenses()
        kwargs['node_license'] = kwargs.get(
            'node_license',
            NodeLicense.find_one(
                Q('name', 'eq', 'No license')
            )
        )
        return super(NodeLicenseRecordFactory, cls)._create(*args, **kwargs)


class IdentifierFactory(ModularOdmFactory):
    class Meta:
        model = Identifier

    referent = SubFactory(RegistrationFactory)
    value = Sequence(lambda n: 'carp:/2460{}'.format(n))

    @classmethod
    def _create(cls, *args, **kwargs):
        kwargs['category'] = kwargs.get('category', 'carpid')

        return super(IdentifierFactory, cls)._create(*args, **kwargs)


def render_generations_from_parent(parent, creator, num_generations):
    current_gen = parent
    for generation in xrange(0, num_generations):
        next_gen = NodeFactory(
            parent=current_gen,
            creator=creator,
            title=fake.sentence(),
            description=fake.paragraph()
        )
        current_gen = next_gen
    return current_gen


def render_generations_from_node_structure_list(parent, creator, node_structure_list):
    new_parent = None
    for node_number in node_structure_list:
        if isinstance(node_number, list):
            render_generations_from_node_structure_list(new_parent or parent, creator, node_number)
        else:
            new_parent = render_generations_from_parent(parent, creator, node_number)
    return new_parent


def create_fake_user():
    email = fake.email()
    name = fake.name()
    parsed = impute_names(name)
    user = UserFactory(
        username=email,
        fullname=name,
        is_registered=True,
        is_claimed=True,
        verification_key=security.random_string(15),
        date_registered=fake.date_time(),
        emails=[email],
        **parsed
    )
    user.set_password('faker123')
    user.save()
    return user


def create_fake_project(creator, n_users, privacy, n_components, name, n_tags, presentation_name, is_registration):
    auth = Auth(user=creator)
    project_title = name if name else fake.sentence()
    if not is_registration:
        project = ProjectFactory(
            title=project_title,
            description=fake.paragraph(),
            creator=creator
        )
    else:
        project = RegistrationFactory(
            title=project_title,
            description=fake.paragraph(),
            creator=creator
        )
    project.set_privacy(privacy)
    for _ in range(n_users):
        contrib = create_fake_user()
        project.add_contributor(contrib, auth=auth)
    if isinstance(n_components, int):
        for _ in range(n_components):
            NodeFactory(
                project=project,
                title=fake.sentence(),
                description=fake.paragraph(),
                creator=creator
            )
    elif isinstance(n_components, list):
        render_generations_from_node_structure_list(project, creator, n_components)
    for _ in range(n_tags):
        project.add_tag(fake.word(), auth=auth)
    if presentation_name is not None:
        project.add_tag(presentation_name, auth=auth)
        project.add_tag('poster', auth=auth)

    project.save()
    return project
