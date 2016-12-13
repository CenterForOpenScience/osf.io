# -*- coding: utf-8 -*-
import functools

import datetime
import mock
from factory import SubFactory
from factory.fuzzy import FuzzyDateTime, FuzzyAttribute, FuzzyChoice
from mock import patch, Mock

import factory
import pytz
from factory.django import DjangoModelFactory
from django.utils import timezone
from faker import Factory
from modularodm.exceptions import NoResultsFound

from osf.models import OSFUser
from website.notifications.constants import NOTIFICATION_TYPES
from website.util import permissions
from website.project.licenses import ensure_licenses
from website.project.model import ensure_schemas
from website.archiver import ARCHIVER_SUCCESS
from framework.auth.core import Auth

from osf import models
from osf.models.sanctions import Sanction
from osf.utils.names import impute_names_model
from osf.modm_compat import Q
from addons.osfstorage.models import OsfStorageFile

fake = Factory.create()
ensure_licenses = functools.partial(ensure_licenses, warn=False)

def get_default_metaschema():
    """This needs to be a method so it gets called after the test database is set up"""
    try:
        return models.MetaSchema.find()[0]
    except IndexError:
        ensure_schemas()
        return models.MetaSchema.find()[0]

def FakeList(provider, n, *args, **kwargs):
    func = getattr(fake, provider)
    return [func(*args, **kwargs) for _ in range(n)]

class UserFactory(DjangoModelFactory):
    # TODO: Change this to only generate long names and see what breaks
    fullname = factory.Sequence(lambda n: 'Freddie Mercury{0}'.format(n))
    
    username = factory.Faker('email')
    password = factory.PostGenerationMethodCall('set_password',
                                                'queenfan86')
    is_registered = True
    is_claimed = True
    date_confirmed = factory.Faker('date_time_this_decade', tzinfo=pytz.utc)
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

class AuthUserFactory(UserFactory):
    """A user that automatically has an api key, for quick authentication.

    Example: ::
        user = AuthUserFactory()
        res = self.app.get(url, auth=user.auth)  # user is "logged in"
    """

    @factory.post_generation
    def add_auth(self, create, extracted):
        self.auth = (self.username, 'queenfan86')

class AuthFactory(factory.base.Factory):
    class Meta:
        model = Auth
    user = factory.SubFactory(UserFactory)

class UnregUserFactory(DjangoModelFactory):
    email = factory.Faker('email')
    fullname = factory.Sequence(lambda n: 'Freddie Mercury{0}'.format(n))
    date_registered = factory.Faker('date_time', tzinfo=pytz.utc)

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
    fullname = factory.Sequence(lambda n: 'Freddie Mercury{0}'.format(n))
    password = 'lolomglgt'

    @classmethod
    def _build(cls, target_class, username, password, fullname):
        '''Build an object without saving it.'''
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time(tzinfo=pytz.utc)
        return instance

    @classmethod
    def _create(cls, target_class, username, password, fullname):
        instance = target_class.create_unconfirmed(
            username=username, password=password, fullname=fullname
        )
        instance.date_registered = fake.date_time(tzinfo=pytz.utc)

        instance.save()
        return instance


class BaseNodeFactory(DjangoModelFactory):
    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    date_created = factory.LazyFunction(timezone.now)
    creator = factory.SubFactory(AuthUserFactory)

    class Meta:
        model = models.Node


class ProjectFactory(BaseNodeFactory):
    category = 'project'


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


class NodeFactory(BaseNodeFactory):
    category = 'hypothesis'
    parent = factory.SubFactory(ProjectFactory)


class InstitutionFactory(DjangoModelFactory):
    name = factory.Faker('company')
    login_url = factory.Faker('url')
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

class PrivateLinkFactory(DjangoModelFactory):
    class Meta:
        model = models.PrivateLink

    name = factory.Faker('word')
    key = factory.Faker('md5')
    anonymous = False
    creator = factory.SubFactory(UserFactory)


class CollectionFactory(DjangoModelFactory):
    class Meta:
        model = models.Collection

    is_bookmark_collection = False
    title = factory.Faker('catch_phrase')
    creator = factory.SubFactory(UserFactory)

class BookmarkCollectionFactory(CollectionFactory):
    is_bookmark_collection = True

class RegistrationFactory(BaseNodeFactory):

    creator = None
    # Default project is created if not provided
    category = 'project'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise Exception('Cannot build registration without saving.')

    @classmethod
    def _create(cls, target_class, project=None, is_public=False,
                schema=None, data=None,
                archive=False, embargo=None, registration_approval=None, retraction=None,
                *args, **kwargs):
        user = None
        if project:
            user = project.creator
        user = kwargs.pop('user', None) or kwargs.get('creator') or user or UserFactory()
        kwargs['creator'] = user
        # Original project to be registered
        project = project or target_class(*args, **kwargs)
        if project.has_permission(user, 'admin'):
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

        with patch('framework.celery_tasks.handlers.enqueue_task'):
            reg = register()
            add_approval_step(reg)
        if not archive:
            with patch.object(reg.archive_job, 'archive_tree_finished', Mock(return_value=True)):
                reg.archive_job.status = ARCHIVER_SUCCESS
                reg.archive_job.save()
                reg.sanction.state = Sanction.APPROVED
                reg.sanction.save()
        # models.ArchiveJob(
        #     src_node=project,
        #     dst_node=reg,
        #     initiator=user,
        # )
        if is_public:
            reg.is_public = True
        reg.save()
        return reg

class WithdrawnRegistrationFactory(BaseNodeFactory):

    @classmethod
    def _create(cls, *args, **kwargs):

        registration = kwargs.pop('registration', None)
        registration.is_public = True
        user = kwargs.pop('user', registration.creator)

        registration.retract_registration(user)
        withdrawal = registration.retraction
        token = withdrawal.approval_state.values()[0]['approval_token']
        with patch('osf.models.AbstractNode.update_search'):
            withdrawal.approve_retraction(user, token)
        withdrawal.save()

        return withdrawal

class SanctionFactory(DjangoModelFactory):
    class Meta:
        abstract = True

    @classmethod
    def _create(cls, target_class, initiated_by=None, approve=False, *args, **kwargs):
        user = kwargs.pop('user', None) or UserFactory()
        kwargs['initiated_by'] = initiated_by or user
        sanction = super(SanctionFactory, cls)._create(target_class, *args, **kwargs)
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
        model = models.Retraction
    user = factory.SubFactory(UserFactory)

class EmbargoFactory(SanctionFactory):
    class Meta:
        model = models.Embargo
    user = factory.SubFactory(UserFactory)

class RegistrationApprovalFactory(SanctionFactory):
    class Meta:
        model = models.RegistrationApproval
    user = factory.SubFactory(UserFactory)

class EmbargoTerminationApprovalFactory(DjangoModelFactory):

    FACTORY_STRATEGY = factory.base.CREATE_STRATEGY

    @classmethod
    def create(cls, registration=None, user=None, embargo=None, *args, **kwargs):
        if registration:
            if not user:
                user = registration.creator
        else:
            user = user or UserFactory()
            if not embargo:
                embargo = EmbargoFactory(state=models.Sanction.APPROVED, approve=True)
                registration = embargo._get_registration()
            else:
                registration = RegistrationFactory(creator=user, user=user, embargo=embargo)
        with mock.patch('osf.models.sanctions.TokenApprovableSanction.ask', mock.Mock()):
            approval = registration.request_embargo_termination(Auth(user))
            return approval


class DraftRegistrationFactory(DjangoModelFactory):
    class Meta:
        model = models.DraftRegistration

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
            registration_schema = registration_schema or models.MetaSchema.find()[0]
        except IndexError:
            ensure_schemas()
        registration_metadata = registration_metadata or {}
        draft = models.DraftRegistration.create_from_node(
            branched_from,
            user=initiator,
            schema=registration_schema,
            data=registration_metadata,
        )
        return draft

class CommentFactory(DjangoModelFactory):
    class Meta:
        model = models.Comment

    content = factory.Sequence(lambda n: 'Comment {0}'.format(n))

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        node = kwargs.pop('node', None) or NodeFactory()
        user = kwargs.pop('user', None) or node.creator
        target = kwargs.pop('target', None) or models.Guid.load(node._id)
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
        target = kwargs.pop('target', None) or models.Guid.load(node._id)
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


class SubjectFactory(DjangoModelFactory):
    text = factory.Sequence(lambda n: 'Example Subject #{}'.format(n))

    class Meta:
        model = models.Subject

    @classmethod
    def _create(cls, target_class, parents=None, *args, **kwargs):
        ret = super(SubjectFactory, cls)._create(target_class, *args, **kwargs)
        if parents:
            ret.parents.add(*parents)
        return ret


class PreprintProviderFactory(DjangoModelFactory):
    name = factory.Faker('company')
    description = factory.Faker('bs')
    external_url = factory.Faker('url')
    logo_name = factory.Faker('file_name', category='image')
    banner_name = factory.Faker('file_name', category='image')

    class Meta:
        model = models.PreprintProvider


class PreprintFactory(DjangoModelFactory):
    doi = factory.Sequence(lambda n: '10.123/{}'.format(n))
    provider = factory.SubFactory(PreprintProviderFactory)
    external_url = 'http://hello.org'

    class Meta:
        model = models.PreprintService

    @classmethod
    def _create(cls, target_class, project=None, filename='preprint_file.txt', provider=None,
                doi=None, external_url=None, is_published=True, subjects=None, finish=True, *args, **kwargs):
        user = None
        if project:
            user = project.creator
        user = kwargs.get('user') or kwargs.get('creator') or user or UserFactory()
        kwargs['creator'] = user
        # Original project to be converted to a preprint
        project = project or ProjectFactory(*args, **kwargs)
        project.save()
        if not project.is_contributor(user):
            project.add_contributor(
                contributor=user,
                permissions=permissions.CREATOR_PERMISSIONS,
                log=False,
                save=True
            )

        file = OsfStorageFile.create(
            is_file=True,
            node=project,
            path='/{}'.format(filename),
            name=filename,
            materialized_path='/{}'.format(filename))
        file.save()

        preprint = target_class(node=project, provider=provider)

        auth = Auth(project.creator)

        if finish:
            preprint.set_primary_file(file, auth=auth)
            subjects = subjects or [[SubjectFactory()._id]]
            preprint.set_subjects(subjects, auth=auth)
            preprint.set_published(is_published, auth=auth)

        if not preprint.is_published:
            project._has_abandoned_preprint = True

        project.preprint_article_doi = doi
        project.save()
        preprint.save()

        return preprint


class TagFactory(DjangoModelFactory):
    class Meta:
        model = models.Tag

    name = factory.Faker('word')
    system = False


class ApiOAuth2PersonalTokenFactory(DjangoModelFactory):
    class Meta:
        model = models.ApiOAuth2PersonalToken

    owner = factory.SubFactory(UserFactory)

    scopes = 'osf.full_write osf.full_read'

    name = factory.Sequence(lambda n: 'Example OAuth2 Personal Token #{}'.format(n))


class ApiOAuth2ApplicationFactory(DjangoModelFactory):
    class Meta:
        model = models.ApiOAuth2Application

    owner = factory.SubFactory(UserFactory)

    name = factory.Sequence(lambda n: 'Example OAuth2 Application #{}'.format(n))

    home_url = 'ftp://ftp.ncbi.nlm.nimh.gov/'
    callback_url = 'http://example.uk'


class AlternativeCitationFactory(DjangoModelFactory):
    class Meta:
        model = models.AlternativeCitation

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


class ForkFactory(DjangoModelFactory):
    class Meta:
        model = models.Node

    @classmethod
    def _create(cls, *args, **kwargs):

        project = kwargs.pop('project', None)
        user = kwargs.pop('user', project.creator)
        title = kwargs.pop('title', None)

        fork = project.fork_node(auth=Auth(user), title=title)
        fork.save()
        return fork


class IdentifierFactory(DjangoModelFactory):
    class Meta:
        model = models.Identifier

    referent = factory.SubFactory(RegistrationFactory)
    value = factory.Sequence(lambda n: 'carp:/2460{}'.format(n))

    @classmethod
    def _create(cls, *args, **kwargs):
        kwargs['category'] = kwargs.get('category', 'carpid')

        return super(IdentifierFactory, cls)._create(*args, **kwargs)


class NodeRelationFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeRelation

    child = factory.SubFactory(NodeFactory)
    parent = factory.SubFactory(NodeFactory)


class ExternalAccountFactory(DjangoModelFactory):
    class Meta:
        model = models.ExternalAccount
    oauth_key = 'some-silly-key'
    oauth_secret = 'some-super-secret'
    provider = 'mock2'
    provider_id = factory.Sequence(lambda n: 'user-{0}'.format(n))
    provider_name = 'Fake Provider'
    display_name = factory.Sequence(lambda n: 'user-{0}'.format(n))
    profile_url = 'http://wutwut.com/'
    refresh_token = 'some-sillier-key'


class MockOAuth2Provider(models.ExternalProvider):
    name = "Mock OAuth 2.0 Provider"
    short_name = "mock2"

    client_id = "mock2_client_id"
    client_secret = "mock2_client_secret"

    auth_url_base = "https://mock2.com/auth"
    callback_url = "https://mock2.com/callback"
    auto_refresh_url = "https://mock2.com/callback"
    refresh_time = 300
    expiry_time = 9001

    def handle_callback(self, response):
        return {
            'provider_id': 'mock_provider_id'
        }


class NotificationSubscriptionFactory(DjangoModelFactory):
    class Meta:
        model = models.NotificationSubscription


def make_node_lineage():
    node1 = NodeFactory()
    node2 = NodeFactory(parent=node1)
    node3 = NodeFactory(parent=node2)
    node4 = NodeFactory(parent=node3)

    return [node1._id, node2._id, node3._id, node4._id]


class NotificationDigestFactory(DjangoModelFactory):
    timestamp = FuzzyDateTime(datetime.datetime(1970, 1, 1, tzinfo=pytz.UTC))
    node_lineage = FuzzyAttribute(fuzzer=make_node_lineage)
    user = factory.SubFactory(UserFactory)
    send_type = FuzzyChoice(choices=NOTIFICATION_TYPES.keys())
    message = fake.text(max_nb_chars=2048)
    event = fake.text(max_nb_chars=50)
    class Meta:
        model = models.NotificationDigest


class ConferenceFactory(DjangoModelFactory):
    class Meta:
        model = models.Conference

    endpoint = factory.Sequence(lambda n: 'conference{0}'.format(n))
    name = factory.Faker('catch_phrase')
    active = True
    is_meeting = True

    @factory.post_generation
    def admins(self, create, extracted, **kwargs):
        self.admins = extracted or [UserFactory()]


class SessionFactory(DjangoModelFactory):
    class Meta:
        model = models.Session

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


class ArchiveJobFactory(DjangoModelFactory):
    class Meta:
        model = models.ArchiveJob
