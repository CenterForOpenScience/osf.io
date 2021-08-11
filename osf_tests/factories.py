# -*- coding: utf-8 -*-
import time

import datetime
import mock
from factory import SubFactory
from factory.fuzzy import FuzzyDateTime, FuzzyAttribute, FuzzyChoice
from mock import patch, Mock

import factory
import pytz
import factory.django
from factory.django import DjangoModelFactory
from django.apps import apps
from django.utils import timezone
from django.contrib.contenttypes.models import ContentType
from django.db.utils import IntegrityError
from faker import Factory
from waffle.models import Flag, Sample, Switch

from website.notifications.constants import NOTIFICATION_TYPES
from osf.utils import permissions
from website.archiver import ARCHIVER_SUCCESS
from website.settings import FAKE_EMAIL_NAME, FAKE_EMAIL_DOMAIN
from framework.auth.core import Auth

from osf import models
from osf.models.sanctions import Sanction
from osf.models.storage import PROVIDER_ASSET_NAME_CHOICES
from osf.utils.names import impute_names_model
from osf.utils.workflows import DefaultStates, DefaultTriggers
from addons.osfstorage.models import OsfStorageFile, Region

fake = Factory.create()

# If tests are run on really old processors without high precision this might fail. Unlikely to occur.
fake_email = lambda: '{}+{}@{}'.format(FAKE_EMAIL_NAME, int(time.clock() * 1000000), FAKE_EMAIL_DOMAIN)

# Do this out of a cls context to avoid setting "t" as a local
PROVIDER_ASSET_NAME_CHOICES = tuple([t[0] for t in PROVIDER_ASSET_NAME_CHOICES])

def get_default_metaschema():
    """This needs to be a method so it gets called after the test database is set up"""
    return models.RegistrationSchema.objects.first()


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

    @factory.post_generation
    def set_emails(self, create, extracted):
        if not self.emails.filter(address=self.username).exists():
            if not self.id:
                if create:
                    # Perform implicit save to populate M2M
                    self.save(clean=False)
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
        """Build an object without saving it."""
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
        """Build an object without saving it."""
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

    #Fix for adding the deleted date.
    @classmethod
    def _create(cls, *args, **kwargs):
        if kwargs.get('is_deleted', None):
            kwargs['deleted'] = timezone.now()
        return super(BaseNodeFactory, cls)._create(*args, **kwargs)


class ProjectFactory(BaseNodeFactory):
    category = 'project'


class DraftNodeFactory(BaseNodeFactory):
    category = 'project'

    class Meta:
        model = models.DraftNode


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
        """Build an object without saving it."""
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

    name = factory.Sequence(lambda n: 'Example Private Link #{}'.format(n))
    key = factory.Faker('md5')
    anonymous = False
    creator = factory.SubFactory(UserFactory)

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        instance = super(PrivateLinkFactory, cls)._create(target_class, *args, **kwargs)
        if instance.is_deleted and not instance.deleted:
            instance.deleted = timezone.now()
            instance.save()
        return instance


class CollectionFactory(DjangoModelFactory):
    class Meta:
        model = models.Collection

    is_bookmark_collection = False
    title = factory.Faker('catch_phrase')
    creator = factory.SubFactory(UserFactory)

    @classmethod
    def _create(cls, *args, **kwargs):
        collected_types = kwargs.pop('collected_types', ContentType.objects.filter(app_label='osf', model__in=['abstractnode', 'basefilenode', 'collection', 'preprint']))
        obj = cls._build(*args, **kwargs)
        obj.save()
        # M2M, requires initial save
        obj.collected_types.add(*collected_types)
        return obj

class BookmarkCollectionFactory(CollectionFactory):
    is_bookmark_collection = True


class CollectionProviderFactory(DjangoModelFactory):
    name = factory.Faker('company')
    description = factory.Faker('bs')
    external_url = factory.Faker('url')

    class Meta:
        model = models.CollectionProvider

    @classmethod
    def _create(cls, *args, **kwargs):
        user = kwargs.pop('creator', None)
        obj = cls._build(*args, **kwargs)
        obj._creator = user or UserFactory()  # Generates primary_collection
        obj.save()
        return obj


class RegistrationProviderFactory(DjangoModelFactory):
    name = factory.Faker('company')
    description = factory.Faker('bs')
    external_url = factory.Faker('url')
    access_token = factory.Faker('bs')
    share_source = factory.Sequence(lambda n: 'share source #{0}'.format(n))

    class Meta:
        model = models.RegistrationProvider

    @classmethod
    def _create(cls, *args, **kwargs):
        user = kwargs.pop('creator', None)
        _id = kwargs.pop('_id', None)
        try:
            obj = cls._build(*args, **kwargs)
        except IntegrityError as e:
            # This is to ensure legacy tests don't fail when their _ids aren't unique
            if _id == models.RegistrationProvider.default__id:
                pass
            else:
                raise e
        if _id and _id != 'osf':
            obj._id = _id

        obj._creator = user or models.OSFUser.objects.first() or UserFactory()  # Generates primary_collection
        obj.save()
        return obj


class OSFGroupFactory(DjangoModelFactory):
    name = factory.Faker('company')
    created = factory.LazyFunction(timezone.now)
    creator = factory.SubFactory(AuthUserFactory)

    class Meta:
        model = models.OSFGroup


class RegistrationFactory(BaseNodeFactory):

    creator = None
    # Default project is created if not provided
    category = 'project'

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        raise Exception('Cannot build registration without saving.')

    @classmethod
    def _create(cls, target_class, project=None, is_public=False,
                schema=None, draft_registration=None,
                archive=False, embargo=None, registration_approval=None, retraction=None,
                provider=None,
                *args, **kwargs):
        user = None
        if project:
            user = project.creator
        user = kwargs.pop('user', None) or kwargs.get('creator') or user or UserFactory()
        kwargs['creator'] = user
        provider = provider or models.RegistrationProvider.get_default()
        # Original project to be registered
        project = project or target_class(*args, **kwargs)
        if project.is_admin_contributor(user):
            project.add_contributor(
                contributor=user,
                permissions=permissions.CREATOR_PERMISSIONS,
                log=False,
                save=False
            )
        project.save()

        # Default registration parameters
        schema = schema or get_default_metaschema()
        if not draft_registration:
            draft_registration = DraftRegistrationFactory(
                branched_from=project,
                initator=user,
                registration_schema=schema,
                provider=provider
            )
        auth = Auth(user=user)
        register = lambda: project.register_node(
            schema=schema,
            auth=auth,
            draft_registration=draft_registration,
            provider=provider,
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
                archive_job.save()
                reg.sanction.state = Sanction.APPROVED
                reg.sanction.save()
        if is_public:
            reg.is_public = True
        reg.files_count = reg.registered_from.files.filter(deleted_on__isnull=True).count()
        draft_registration.registered_node = reg
        draft_registration.save()
        reg.save()
        return reg


class WithdrawnRegistrationFactory(BaseNodeFactory):

    @classmethod
    def _create(cls, *args, **kwargs):

        registration = kwargs.pop('registration', RegistrationFactory())
        registration.is_public = True
        user = kwargs.pop('user', registration.creator)

        registration.retract_registration(user)
        withdrawal = registration.retraction
        token = list(withdrawal.approval_state.values())[0]['approval_token']
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
        sanction = super()._create(target_class, *args, **kwargs)
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
        with mock.patch('osf.models.sanctions.EmailApprovableSanction.ask', mock.Mock()):
            approval = registration.request_embargo_termination(user)
            return approval


class DraftRegistrationFactory(DjangoModelFactory):
    class Meta:
        model = models.DraftRegistration

    @classmethod
    def _create(cls, *args, **kwargs):
        title = kwargs.pop('title', None)
        initiator = kwargs.get('initiator', None)
        description = kwargs.pop('description', None)
        branched_from = kwargs.get('branched_from', None)
        registration_schema = kwargs.get('registration_schema')
        registration_metadata = kwargs.get('registration_metadata')
        provider = kwargs.get('provider')
        branched_from_creator = branched_from.creator if branched_from else None
        initiator = initiator or branched_from_creator or kwargs.get('user', None) or kwargs.get('creator', None) or UserFactory()
        registration_schema = registration_schema or get_default_metaschema()
        registration_metadata = registration_metadata or {}
        provider = provider or models.RegistrationProvider.get_default()
        provider.schemas.add(registration_schema)
        draft = models.DraftRegistration.create_from_node(
            node=branched_from,
            user=initiator,
            schema=registration_schema,
            data=registration_metadata,
            provider=provider,
        )
        if title:
            draft.title = title
        if description:
            draft.description = description
        draft.registration_responses = draft.flatten_registration_metadata()
        draft.save()
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
    _id = factory.Sequence(lambda n: f'slug{n}')

    name = factory.Faker('company')
    description = factory.Faker('bs')
    external_url = factory.Faker('url')
    share_source = factory.Sequence(lambda n: 'share source #{0}'.format(n))

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
    from website import settings
    doi = settings.DOI_FORMAT.format(prefix=preprint.provider.doi_prefix, guid=preprint._id)
    preprint.set_identifier_values(doi=doi)


class PreprintFactory(DjangoModelFactory):
    class Meta:
        model = models.Preprint

    title = factory.Faker('catch_phrase')
    description = factory.Faker('sentence')
    created = factory.LazyFunction(timezone.now)
    creator = factory.SubFactory(AuthUserFactory)

    doi = factory.Sequence(lambda n: '10.123/{}'.format(n))
    provider = factory.SubFactory(PreprintProviderFactory)

    @classmethod
    def _build(cls, target_class, *args, **kwargs):
        creator = kwargs.pop('creator', None) or UserFactory()
        provider = kwargs.pop('provider', None) or PreprintProviderFactory()
        project = kwargs.pop('project', None) or None
        title = kwargs.pop('title', None) or 'Untitled'
        description = kwargs.pop('description', None) or 'None'
        is_public = kwargs.pop('is_public', True)
        instance = target_class(provider=provider, title=title, description=description, creator=creator, node=project, is_public=is_public)
        return instance

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        update_task_patcher = mock.patch('website.preprints.tasks.on_preprint_updated.si')
        update_task_patcher.start()

        finish = kwargs.pop('finish', True)
        set_doi = kwargs.pop('set_doi', True)
        is_published = kwargs.pop('is_published', True)
        instance = cls._build(target_class, *args, **kwargs)
        file_size = kwargs.pop('file_size', 1337)

        doi = kwargs.pop('doi', None)
        license_details = kwargs.pop('license_details', None)
        filename = kwargs.pop('filename', None) or 'preprint_file.txt'
        subjects = kwargs.pop('subjects', None) or [[SubjectFactory()._id]]
        instance.article_doi = doi

        user = kwargs.pop('creator', None) or instance.creator
        instance.save()

        preprint_file = OsfStorageFile.create(
            target_object_id=instance.id,
            target_content_type=ContentType.objects.get_for_model(instance),
            path='/{}'.format(filename),
            name=filename,
            materialized_path='/{}'.format(filename))

        instance.machine_state = kwargs.pop('machine_state', 'initial')
        preprint_file.save()
        from addons.osfstorage import settings as osfstorage_settings

        preprint_file.create_version(user, {
            'object': '06d80e',
            'service': 'cloud',
            osfstorage_settings.WATERBUTLER_RESOURCE: 'osf',
        }, {
            'size': file_size,
            'contentType': 'img/png'
        }).save()
        update_task_patcher.stop()
        if finish:
            auth = Auth(user)

            instance.set_primary_file(preprint_file, auth=auth, save=True)
            instance.set_subjects(subjects, auth=auth)
            if license_details:
                instance.set_preprint_license(license_details, auth=auth)
            instance.set_published(is_published, auth=auth)
            create_task_patcher = mock.patch('website.identifiers.utils.request_identifiers')
            mock_create_identifier = create_task_patcher.start()
            if is_published and set_doi:
                mock_create_identifier.side_effect = sync_set_identifiers(instance)
            create_task_patcher.stop()

        instance.save()
        return instance

class TagFactory(DjangoModelFactory):
    class Meta:
        model = models.Tag

    name = factory.Sequence(lambda n: 'Example Tag #{}'.format(n))
    system = False

class DismissedAlertFactory(DjangoModelFactory):
    class Meta:
        model = models.DismissedAlert

    @classmethod
    def _create(cls, *args, **kwargs):
        kwargs['_id'] = kwargs.get('_id', 'adblock')
        kwargs['user'] = kwargs.get('user', UserFactory())
        kwargs['location'] = kwargs.get('location', 'iver/settings')

        return super(DismissedAlertFactory, cls)._create(*args, **kwargs)

class ApiOAuth2ScopeFactory(DjangoModelFactory):
    class Meta:
        model = models.ApiOAuth2Scope

    name = factory.Sequence(lambda n: 'scope{}'.format(n))
    is_public = True
    is_active = True
    description = factory.Faker('text')

class ApiOAuth2PersonalTokenFactory(DjangoModelFactory):
    class Meta:
        model = models.ApiOAuth2PersonalToken

    owner = factory.SubFactory(UserFactory)
    name = factory.Sequence(lambda n: 'Example OAuth2 Personal Token #{}'.format(n))

    @classmethod
    def _create(cls, *args, **kwargs):
        token = super(ApiOAuth2PersonalTokenFactory, cls)._create(*args, **kwargs)
        token.scopes.add(ApiOAuth2ScopeFactory())
        return token

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
        self.admins.add(*(extracted or [UserFactory()]))


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
    color = factory.Faker('color')
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

    creator = factory.SubFactory(AuthUserFactory)
    target = factory.SubFactory(NodeFactory)

    comment = factory.Faker('text')

class PreprintRequestFactory(DjangoModelFactory):
    class Meta:
        model = models.PreprintRequest

    comment = factory.Faker('text')

osfstorage_settings = apps.get_app_config('addons_osfstorage')


generic_location = {
    'service': 'cloud',
    osfstorage_settings.WATERBUTLER_RESOURCE: 'resource',
    'object': '1615307',
}

generic_waterbutler_settings = {
    'storage': {
        'provider': 'glowcloud',
        'container': 'osf_storage',
        'use_public': True,
    }
}

generic_waterbutler_credentials = {
    'storage': {
        'region': 'PartsUnknown',
        'username': 'mankind',
        'token': 'heresmrsocko'
    }
}


class RegionFactory(DjangoModelFactory):
    class Meta:
        model = Region

    name = factory.Sequence(lambda n: 'Region {0}'.format(n))
    _id = factory.Sequence(lambda n: 'us_east_{0}'.format(n))
    waterbutler_credentials = generic_waterbutler_credentials
    waterbutler_settings = generic_waterbutler_settings
    waterbutler_url = 'http://123.456.test.woo'


class ProviderAssetFileFactory(DjangoModelFactory):
    class Meta:
        model = models.ProviderAssetFile

    name = FuzzyChoice(choices=PROVIDER_ASSET_NAME_CHOICES)
    file = factory.django.FileField(filename=factory.Faker('text'))

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        providers = kwargs.pop('providers', [])
        instance = super(ProviderAssetFileFactory, cls)._create(target_class, *args, **kwargs)
        instance.providers.add(*providers)
        instance.save()
        return instance

class ChronosJournalFactory(DjangoModelFactory):
    class Meta:
        model = models.ChronosJournal

    name = factory.Faker('company')
    title = factory.Faker('sentence')
    journal_id = factory.Faker('ean')

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        kwargs['raw_response'] = kwargs.get('raw_response', {
            'TITLE': kwargs.get('title', factory.Faker('sentence').generate([])),
            'JOURNAL_ID': kwargs.get('title', factory.Faker('ean').generate([])),
            'NAME': kwargs.get('name', factory.Faker('company').generate([])),
            'JOURNAL_URL': factory.Faker('url').generate([]),
            'PUBLISHER_ID': factory.Faker('ean').generate([]),
            'PUBLISHER_NAME': factory.Faker('name').generate([])
            # Other stuff too probably
        })
        instance = super(ChronosJournalFactory, cls)._create(target_class, *args, **kwargs)
        instance.save()
        return instance


class ChronosSubmissionFactory(DjangoModelFactory):
    class Meta:
        model = models.ChronosSubmission

    publication_id = factory.Faker('ean')
    journal = factory.SubFactory(ChronosJournalFactory)
    preprint = factory.SubFactory(PreprintFactory)
    submitter = factory.SubFactory(AuthUserFactory)
    status = factory.Faker('random_int', min=1, max=5)
    submission_url = factory.Faker('url')

    @classmethod
    def _create(cls, target_class, *args, **kwargs):
        kwargs['raw_response'] = kwargs.get('raw_response', {
            'PUBLICATION_ID': kwargs.get('publication_id', factory.Faker('ean').generate([])),
            'STATUS_CODE': kwargs.get('status', factory.Faker('random_int', min=1, max=5).generate([])),
            'CHRONOS_SUBMISSION_URL': kwargs.get('submission_url', factory.Faker('url').generate([])),
            # Other stuff too probably
        })
        instance = super(ChronosSubmissionFactory, cls)._create(target_class, *args, **kwargs)
        instance.save()
        return instance


class BrandFactory(DjangoModelFactory):
    class Meta:
        model = models.Brand

    # just limiting it to 30 chars
    name = factory.LazyAttribute(lambda n: fake.company()[:29])

    hero_logo_image = factory.Faker('url')
    topnav_logo_image = factory.Faker('url')
    hero_background_image = factory.Faker('url')

    primary_color = factory.Faker('hex_color')
    secondary_color = factory.Faker('hex_color')
