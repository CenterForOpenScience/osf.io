# -*- coding: utf-8 -*-
import requests

from django.apps import apps
from django.contrib.postgres import fields
from django.core.exceptions import ValidationError
from typedmodels.models import TypedModel
from api.taxonomies.utils import optimize_subject_query
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from dirtyfields import DirtyFieldsMixin
from guardian.models import GroupObjectPermissionBase, UserObjectPermissionBase

from framework import sentry
from osf.models.base import BaseModel, TypedObjectIDMixin
from osf.models.licenses import NodeLicense
from osf.models.mixins import ReviewProviderMixin
from osf.models.storage import ProviderAssetFile
from osf.models.subject import Subject
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.workflows import RegistrationModerationStates
from osf.utils.fields import EncryptedTextField
from osf.utils.permissions import REVIEW_PERMISSIONS
from website import settings
from website.util import api_v2_url
from functools import reduce
from osf.models.notifications import NotificationSubscription


class AbstractProvider(TypedModel, TypedObjectIDMixin, ReviewProviderMixin, DirtyFieldsMixin, BaseModel):
    class Meta:
        unique_together = ('_id', 'type')
        permissions = REVIEW_PERMISSIONS

    PUSH_SHARE_TYPE_CHOICES = (
        ('Preprint', 'Preprint'),
        ('Thesis', 'Thesis'),
        ('Registration', 'Registration'),
    )
    PUSH_SHARE_TYPE_HELP = 'This SHARE type will be used when pushing publications to SHARE'

    default__id = 'osf'

    @classmethod
    def get_default(cls):
        return cls.objects.get(_id=cls.default__id)

    primary_collection = models.ForeignKey('Collection', related_name='+',
                                           null=True, blank=True, on_delete=models.SET_NULL)
    name = models.CharField(null=False, max_length=128)  # max length on prod: 22
    advisory_board = models.TextField(default='', blank=True)
    description = models.TextField(default='', blank=True)
    domain = models.URLField(blank=True, default='', max_length=200)
    domain_redirect_enabled = models.BooleanField(default=False)
    external_url = models.URLField(null=True, blank=True, max_length=200)  # max length on prod: 25
    email_contact = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 23
    email_support = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 23
    social_twitter = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8
    social_facebook = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8
    social_instagram = models.CharField(null=True, blank=True, max_length=200)  # max length on prod: 8
    footer_links = models.TextField(default='', blank=True)
    facebook_app_id = models.BigIntegerField(blank=True, null=True)
    example = models.CharField(null=True, blank=True, max_length=20)  # max length on prod: 5
    licenses_acceptable = models.ManyToManyField(NodeLicense, blank=True, related_name='licenses_acceptable')
    default_license = models.ForeignKey(NodeLicense, related_name='default_license',
                                        null=True, blank=True, on_delete=models.CASCADE)
    allow_submissions = models.BooleanField(default=True)
    allow_commenting = models.BooleanField(default=False)
    access_token = EncryptedTextField(null=True, blank=True)

    brand = models.ForeignKey('Brand', related_name='providers', null=True, blank=True, on_delete=models.SET_NULL)

    branded_discovery_page = models.BooleanField(default=True)
    advertises_on_discovery = models.BooleanField(default=True)
    has_landing_page = models.BooleanField(default=False)

    share_publish_type = models.CharField(
        choices=PUSH_SHARE_TYPE_CHOICES,
        help_text=PUSH_SHARE_TYPE_HELP,
        default='Thesis',
        max_length=32
    )
    share_source = models.CharField(blank=True, default='', max_length=200)
    share_title = models.TextField(default='', blank=True)
    access_token = EncryptedTextField(null=True, blank=True)

    def __repr__(self):
        return ('(name={self.name!r}, default_license={self.default_license!r}, '
                'allow_submissions={self.allow_submissions!r}) with id {self.id!r}').format(self=self)

    def __str__(self):
        return '[{}] {} - {}'.format(self.readable_type, self.name, self.id)

    @property
    def all_subjects(self):
        if self.subjects.exists():
            return self.subjects.all()
        return Subject.objects.filter(
            provider___id='osf',
            provider__type='osf.preprintprovider',
        )

    @property
    def has_highlighted_subjects(self):
        return self.subjects.filter(highlighted=True).exists()

    @property
    def highlighted_subjects(self):
        if self.has_highlighted_subjects:
            return self.subjects.filter(highlighted=True).order_by('text')[:10]
        else:
            return sorted(self.top_level_subjects, key=lambda s: s.text)[:10]

    @property
    def top_level_subjects(self):
        if self.subjects.exists():
            return optimize_subject_query(self.subjects.filter(parent__isnull=True))
        return optimize_subject_query(Subject.objects.filter(
            parent__isnull=True,
            provider___id='osf',
            provider__type='osf.preprintprovider',
        ))

    @property
    def readable_type(self):
        raise NotImplementedError

    def get_asset_url(self, name):
        """ Helper that returns an associated ProviderAssetFile's url, or None

        :param str name: Name to perform lookup by
        :returns str|None: url of file
        """
        try:
            return self.asset_files.get(name=name).file.url
        except ProviderAssetFile.DoesNotExist:
            return None

    def setup_share_source(self, provider_home_page):
        if self.access_token:
            raise ValidationError('Cannot update access_token because one or the other already exists')
        if not settings.SHARE_ENABLED or not settings.SHARE_URL:
            raise ValidationError('SHARE_ENABLED is set to false')
        if not self.get_asset_url('square_color_no_transparent'):
            raise ValidationError('Unable to find "square_color_no_transparent" icon for provider')

        if settings.SHARE_PROVIDER_PREPEND:
            share_provider_name = f'{settings.SHARE_PROVIDER_PREPEND}_{self.name}'
        else:
            share_provider_name = self.name

        resp = requests.post(
            f'{settings.SHARE_URL}api/v2/sources/',
            json={
                'data': {
                    'type': 'Source',
                    'attributes': {
                        'homePage': provider_home_page,
                        'longTitle': share_provider_name,
                        'iconUrl': self.get_asset_url('square_color_no_transparent')
                    }
                }
            },
            headers={
                'Authorization': f'Bearer {settings.SHARE_API_TOKEN}',
                'Content-Type': 'application/vnd.api+json'
            }
        )
        resp.raise_for_status()
        resp_json = resp.json()

        self.share_source = resp_json['data']['attributes']['longTitle']
        for data in resp_json['included']:
            if data['type'] == 'ShareUser':
                self.access_token = data['attributes']['token']

        self.save()


class CollectionProvider(AbstractProvider):

    class Meta:
        permissions = (
            # custom permissions for use in the OSF Admin App
            ('view_collectionprovider', 'Can view collection provider details'),
        )

    @property
    def readable_type(self):
        return 'collection'

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_api_v2_url(self):
        path = '/providers/collections/{}/'.format(self._id)
        return api_v2_url(path)


class RegistrationProvider(AbstractProvider):
    REVIEWABLE_RELATION_NAME = 'registrations'
    REVIEW_STATES = RegistrationModerationStates
    STATE_FIELD_NAME = 'moderation_state'

    DEFAULT_SUBSCRIPTIONS = ['new_pending_submissions', 'new_pending_withdraw_requests']

    def __init__(self, *args, **kwargs):
        self._meta.get_field('share_publish_type').default = 'Registration'
        super().__init__(*args, **kwargs)

    class Meta:
        permissions = (
            # custom permissions for use in the OSF Admin App
            ('view_registrationprovider', 'Can view registration provider details'),
        )

    @property
    def is_default(self):
        return self._id == self.default__id

    @property
    def readable_type(self):
        return 'registration'

    def get_absolute_url(self):
        return self.absolute_api_v2_url

    @property
    def absolute_api_v2_url(self):
        path = '/providers/registrations/{}/'.format(self._id)
        return api_v2_url(path)

    def validate_schema(self, schema):
        if not self.schemas.filter(id=schema.id).exists():
            raise ValidationError('Invalid schema for provider.')


class PreprintProvider(AbstractProvider):

    def __init__(self, *args, **kwargs):
        self._meta.get_field('share_publish_type').default = 'Preprint'
        super().__init__(*args, **kwargs)

    PUSH_SHARE_TYPE_HELP = 'This SHARE type will be used when pushing publications to SHARE'

    REVIEWABLE_RELATION_NAME = 'preprints'

    additional_providers = fields.ArrayField(models.CharField(max_length=200), default=list, blank=True)
    doi_prefix = models.CharField(blank=True, max_length=32)
    in_sloan_study = models.NullBooleanField(default=True)

    PREPRINT_WORD_CHOICES = (
        ('preprint', 'Preprint'),
        ('paper', 'Paper'),
        ('thesis', 'Thesis'),
        ('work', 'Work'),
        ('none', 'None')
    )
    preprint_word = models.CharField(max_length=10, choices=PREPRINT_WORD_CHOICES, default='preprint')
    subjects_acceptable = DateTimeAwareJSONField(blank=True, default=list)

    class Meta:
        permissions = (
            # custom permissions for use in the OSF Admin App
            ('view_preprintprovider', 'Can view preprint provider details'),
        )

    @property
    def readable_type(self):
        return 'preprint'

    @property
    def all_subjects(self):
        if self.subjects.exists():
            return self.subjects.all()
        else:
            # TODO: Delet this when all PreprintProviders have a mapping
            return rules_to_subjects(self.subjects_acceptable)

    @property
    def has_highlighted_subjects(self):
        return self.subjects.filter(highlighted=True).exists()

    @property
    def highlighted_subjects(self):
        if self.has_highlighted_subjects:
            return self.subjects.filter(highlighted=True).order_by('text')[:10]
        else:
            return sorted(self.top_level_subjects, key=lambda s: s.text)[:10]

    @property
    def top_level_subjects(self):
        if self.subjects.exists():
            return optimize_subject_query(self.subjects.filter(parent__isnull=True))
        else:
            # TODO: Delet this when all PreprintProviders have a mapping
            if len(self.subjects_acceptable) == 0:
                return optimize_subject_query(Subject.objects.filter(parent__isnull=True, provider___id='osf'))
            tops = set([sub[0][0] for sub in self.subjects_acceptable])
            return [Subject.load(sub) for sub in tops]

    @property
    def landing_url(self):
        return self.domain if self.domain else '{}preprints/{}'.format(settings.DOMAIN, self._id)

    def get_absolute_url(self):
        return '{}preprint_providers/{}'.format(self.absolute_api_v2_url, self._id)

    @property
    def absolute_api_v2_url(self):
        path = '/providers/preprints/{}/'.format(self._id)
        return api_v2_url(path)

def rules_to_subjects(rules):
    if not rules:
        return Subject.objects.filter(provider___id='osf', provider__type='osf.preprintprovider')
    q = []
    for rule in rules:
        parent_from_rule = Subject.load(rule[0][-1])
        if rule[1]:
            q.append(models.Q(parent=parent_from_rule))
            if len(rule[0]) == 1:
                potential_parents = Subject.objects.filter(parent=parent_from_rule)
                for parent in potential_parents:
                    q.append(models.Q(parent=parent))
        for sub in rule[0]:
            q.append(models.Q(_id=sub))
    return Subject.objects.filter(reduce(lambda x, y: x | y, q)) if len(q) > 1 else (Subject.objects.filter(q[0]) if len(q) else Subject.objects.filter(provider___id='osf', provider__type='osf.preprintprovider'))


@receiver(post_save, sender=PreprintProvider)
@receiver(post_save, sender=RegistrationProvider)
def create_provider_auth_groups(sender, instance, created, **kwargs):
    if created:
        instance.update_group_permissions()


@receiver(post_save, sender=PreprintProvider)
@receiver(post_save, sender=RegistrationProvider)
def create_provider_notification_subscriptions(sender, instance, created, **kwargs):
    if created:
        for subscription in instance.DEFAULT_SUBSCRIPTIONS:
            NotificationSubscription.objects.get_or_create(
                _id=f'{instance._id}_{subscription}',
                event_name=subscription,
                provider=instance
            )


@receiver(post_save, sender=CollectionProvider)
@receiver(post_save, sender=RegistrationProvider)
def create_primary_collection_for_provider(sender, instance, created, **kwargs):
    if created:
        Collection = apps.get_model('osf.Collection')
        user = getattr(instance, '_creator', None)  # Temp attr set in admin view
        if user:
            c = Collection(
                title='{}\'s Collection'.format(instance.name),
                creator=user,
                provider=instance,
                is_promoted=True,
                is_public=True
            )
            c.save()
            instance.primary_collection = c
            instance.save()
        else:
            # A user is required for Collections / Groups
            sentry.log_message('Unable to create primary_collection for {}Provider {}'.format(instance.readable_type.capitalize(), instance.name))

class WhitelistedSHAREPreprintProvider(BaseModel):
    id = models.AutoField(primary_key=True)
    provider_name = models.CharField(unique=True, max_length=200)

    def __unicode__(self):
        return self.provider_name


class AbstractProviderUserObjectPermission(UserObjectPermissionBase):
    content_object = models.ForeignKey(AbstractProvider, on_delete=models.CASCADE)


class AbstractProviderGroupObjectPermission(GroupObjectPermissionBase):
    content_object = models.ForeignKey(AbstractProvider, on_delete=models.CASCADE)
