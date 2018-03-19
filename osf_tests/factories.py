# -*- coding: utf-8 -*-
import time

import datetime
import mock
from factory import SubFactory
from factory.fuzzy import FuzzyDateTime, FuzzyAttribute, FuzzyChoice
from mock import patch, Mock

import factory
import pytz
from factory.django import DjangoModelFactory
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError
from faker import Factory
from waffle.models import Flag, Sample, Switch

from website import settings
from website.notifications.constants import NOTIFICATION_TYPES
from osf.utils import permissions
from website.archiver import ARCHIVER_SUCCESS
from website.identifiers.utils import parse_identifiers
from website.settings import FAKE_EMAIL_NAME, FAKE_EMAIL_DOMAIN
from framework.auth.core import Auth

from osf import models
from osf.models.sanctions import Sanction
from osf.utils.names import impute_names_model
from osf.utils.workflows import DefaultStates, DefaultTriggers
from addons.osfstorage.models import OsfStorageFile

fake = Factory.create()

# If tests are run on really old processors without high precision this might fail. Unlikely to occur.
fake_email = lambda: '{}+{}@{}'.format(FAKE_EMAIL_NAME, int(time.clock() * 1000000), FAKE_EMAIL_DOMAIN)

def get_default_metaschema():
    """This needs to be a method so it gets called after the test database is set up"""
    return models.MetaSchema.objects.first()

def FakeList(provider, n, *args, **kwargs):
    func = getattr(fake, provider)
    return [func(*args, **kwargs) for _ in range(n)]

class UserFactory(DjangoModelFactory):
    # TODO: Change this to only generate long names and see what breaks
    fullname = factory.Sequence(lambda n: 'Freddie Mercury{0}'.format(n))

    username = factory.LazyFunction(fake_email)
    password = factory.PostGenerationMethodCall('set_password',
                                                'queenfan86')
    is_registered = True
    is_claimed = True
    date_confirmed = factory.Faker('date_time_this_decade', tzinfo=pytz.utc)
    merged_by = None
    verification_key = None

    class Meta:
        model = models.OSFUser

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        emails = kwargs.pop('emails', [])
        instance = super(DjangoModelFactory, cls)._build(target_class, *args, **kwargs)
        if emails:
            # Save for M2M population
            instance.set_unusable_password()
            instance.save()
        for email in emails:
            instance.emails.create(address=email)
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        emails = kwargs.pop('emails', [])
        instance = super(DjangoModelFactory, cls)._create(target_class, *args, **kwargs)
        if emails and not instance.pk:
            # Save for M2M population
            instance.set_unusable_password()
            instance.save()
        for email in emails:
            instance.emails.create(address=email)
        return instance

    @factory.post_generation
    def set_names(self, create, extracted):
        parsed = impute_names_model(self.fullname)
        for key, value in parsed.items():
            setattr(self, key, value)
        if create:
            self.save()

    @factory.post_generation
    def set_emails(self, create, extracted):
        if not self.emails.filter(address=self.username).exists():
            if not self.id:
                if create:
                    # Perform implicit save to populate M2M
                    self.save()
                else:
                    # This might lead to strange behavior
                    return
            self.emails.create(address=str(self.username).lower())

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
    email = factory.LazyFunction(fake_email)
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
    username = factory.LazyFunction(fake_email)
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
    created = factory.LazyFunction(timezone.now)
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
        kwargs['node_license'] = kwargs.get(
            'node_license',
            models.NodeLicense.objects.get(name='No license')
        )
        return super(NodeLicenseRecordFactory, cls)._create(*args, **kwargs)


class NodeLogFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeLog
    action = 'file_added'
    params = {'path': '/'}
    user = SubFactory(UserFactory)

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

    @classmethod
    def _create(cls, *args, **kwargs):
        collected_types = kwargs.pop('collected_types', ContentType.objects.filter(app_label='osf', model__in=['abstractnode', 'basefilenode', 'collection', 'preprintservice']))
        obj = cls._build(*args, **kwargs)
        obj.save()
        # M2M, requires initial save
        obj.collected_types = collected_types
        return obj

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
                archive_job = reg.archive_job
                archive_job.status = ARCHIVER_SUCCESS
                archive_job.done = True
                reg.sanction.state = Sanction.APPROVED
                reg.sanction.save()
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
        registration_schema = registration_schema or models.MetaSchema.objects.first()
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
    def _create(cls, target_class, parent=None, provider=None, bepress_subject=None, *args, **kwargs):
        provider = provider or models.PreprintProvider.objects.first() or PreprintProviderFactory(_id='osf')
        if provider._id != 'osf' and not bepress_subject:
            osf = models.PreprintProvider.load('osf') or PreprintProviderFactory(_id='osf')
            bepress_subject = SubjectFactory(provider=osf)
        try:
            ret = super(SubjectFactory, cls)._create(target_class, parent=parent, provider=provider, bepress_subject=bepress_subject, *args, **kwargs)
        except IntegrityError:
            ret = models.Subject.objects.get(text=kwargs['text'])
            if parent:
                ret.parent = parent
        return ret


class PreprintProviderFactory(DjangoModelFactory):
    name = factory.Faker('company')
    description = factory.Faker('bs')
    external_url = factory.Faker('url')

    class Meta:
        model = models.PreprintProvider

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        instance = super(PreprintProviderFactory, cls)._build(target_class, *args, **kwargs)
        if not instance.share_title:
            instance.share_title = instance._id
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        instance = super(PreprintProviderFactory, cls)._create(target_class, *args, **kwargs)
        if not instance.share_title:
            instance.share_title = instance._id
            instance.save()
        return instance


def sync_set_identifiers(preprint):
    ezid_return_value = {
        'response': {
            'success': '{doi}osf.io/{guid} | {ark}osf.io/{guid}'.format(
                doi=settings.DOI_NAMESPACE, ark=settings.ARK_NAMESPACE, guid=preprint._id
            )
        },
        'already_exists': False
    }
    id_dict = parse_identifiers(ezid_return_value)
    preprint.set_identifier_values(doi=id_dict['doi'])


class PreprintFactory(DjangoModelFactory):
    class Meta:
        model = models.PreprintService

    doi = factory.Sequence(lambda n: '10.123/{}'.format(n))
    provider = factory.SubFactory(PreprintProviderFactory)

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        creator = kwargs.pop('creator', None) or UserFactory()
        project = kwargs.pop('project', None) or ProjectFactory(creator=creator)
        provider = kwargs.pop('provider', None) or PreprintProviderFactory()
        instance = target_class(node=project, provider=provider)

        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        update_task_patcher = mock.patch('website.preprints.tasks.on_preprint_updated.si')
        update_task_patcher.start()

        finish = kwargs.pop('finish', True)
        is_published = kwargs.pop('is_published', True)
        instance = cls._build(target_class, *args, **kwargs)

        doi = kwargs.pop('doi', None)
        license_details = kwargs.pop('license_details', None)
        filename = kwargs.pop('filename', None) or 'preprint_file.txt'
        subjects = kwargs.pop('subjects', None) or [[SubjectFactory()._id]]
        instance.node.preprint_article_doi = doi

        instance.machine_state = kwargs.pop('machine_state', 'initial')

        user = kwargs.pop('creator', None) or instance.node.creator
        if not instance.node.is_contributor(user):
            instance.node.add_contributor(
                contributor=user,
                permissions=permissions.CREATOR_PERMISSIONS,
                log=False,
                save=True
            )

        preprint_file = OsfStorageFile.create(
            node=instance.node,
            path='/{}'.format(filename),
            name=filename,
            materialized_path='/{}'.format(filename))
        preprint_file.save()

        from addons.osfstorage import settings as osfstorage_settings

        preprint_file.create_version(user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': 1337,
            'contentType': 'img/png'
        }).save()

        if finish:
            auth = Auth(user)

            instance.set_primary_file(preprint_file, auth=auth, save=True)
            instance.set_subjects(subjects, auth=auth)
            if license_details:
                instance.set_preprint_license(license_details, auth=auth)

            create_task_patcher = mock.patch('website.preprints.tasks.get_and_set_preprint_identifiers.si')
            mock_create_identifier = create_task_patcher.start()
            if is_published:
                mock_create_identifier.side_effect = sync_set_identifiers(instance)

            instance.set_published(is_published, auth=auth)
            create_task_patcher.stop()

        if not instance.is_published:
            instance.node._has_abandoned_preprint = True

        instance.node.save()
        instance.save()
        return instance

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
    name = 'Mock OAuth 2.0 Provider'
    short_name = 'mock2'

    client_id = 'mock2_client_id'
    client_secret = 'mock2_client_secret'

    auth_url_base = 'https://mock2.com/auth'
    callback_url = 'https://mock2.com/callback'
    auto_refresh_url = 'https://mock2.com/callback'
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


class ReviewActionFactory(DjangoModelFactory):
    class Meta:
        model = models.ReviewAction

    trigger = FuzzyChoice(choices=DefaultTriggers.values())
    comment = factory.Faker('text')
    from_state = FuzzyChoice(choices=DefaultStates.values())
    to_state = FuzzyChoice(choices=DefaultStates.values())

    target = factory.SubFactory(PreprintFactory)
    creator = factory.SubFactory(AuthUserFactory)

    is_deleted = False

class ScheduledBannerFactory(DjangoModelFactory):
    # Banners are set for 24 hours from start_date if no end date is given
    class Meta:
        model = models.ScheduledBanner

    name = factory.Faker('name')
    default_alt_text = factory.Faker('text')
    mobile_alt_text = factory.Faker('text')
    default_photo = factory.Faker('file_name')
    mobile_photo = factory.Faker('file_name')
    license = factory.Faker('name')
    color = 'white'
    start_date = timezone.now()
    end_date = factory.LazyAttribute(lambda o: o.start_date)

class FlagFactory(DjangoModelFactory):
    name = factory.Faker('catch_phrase')
    everyone = True
    note = 'This is a waffle test flag'

    class Meta:
        model = Flag


class SampleFactory(DjangoModelFactory):
    name = factory.Faker('catch_phrase')
    percent = 100
    note = 'This is a waffle test sample'

    class Meta:
        model = Sample


class SwitchFactory(DjangoModelFactory):
    name = factory.Faker('catch_phrase')
    active = True
    note = 'This is a waffle test switch'

    class Meta:
        model = Switch


class NodeRequestFactory(DjangoModelFactory):
    class Meta:
        model = models.NodeRequest

    comment = factory.Faker('text')
