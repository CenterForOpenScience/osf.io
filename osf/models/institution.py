from enum import Enum
from urllib.parse import urljoin
import logging
from collections.abc import Iterable

from dirtyfields import DirtyFieldsMixin

from django.conf import settings as django_conf_settings
from django.contrib.postgres import fields
from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.urls import reverse
from django.utils import timezone

from framework import sentry
from .base import BaseModel, ObjectIDMixin
from .contributor import InstitutionalContributor
from .institution_affiliation import InstitutionAffiliation
from .institution_storage_region import InstitutionStorageRegion
from .mixins import Loggable, GuardianMixin
from .storage import InstitutionAssetFile
from .validators import validate_email
from osf.utils.fields import NonNaiveDateTimeField, LowercaseEmailField
from website import mails
from website import settings as website_settings

logger = logging.getLogger(__name__)


class IntegrationType(Enum):
    """Defines 5 SSO types for OSF institution integration.
    """

    SAML_SHIBBOLETH = 'saml-shib'  # SSO via SAML (Shibboleth impl) where CAS serves as the SP and institutions as IdP
    CAS_PAC4J = 'cas-pac4j'  # SSO via CAS (pac4j impl) where CAS serves as the client and institution as server
    OAUTH_PAC4J = 'oauth-pac4j'  # SSO via OAuth (pac4j impl) where CAS serves as the client and institution as server
    AFFILIATION_VIA_ORCID = 'via-orcid'  # Using ORCiD SSO for sign in; using ORCiD public API for affiliation
    NONE = ''  # Institution affiliation is done via email domain whitelist w/o SSO


class SsoFilterCriteriaAction(Enum):
    """Defines 2 criteria that when comparing filter attributes for shared SSO and selective SSO.
    """
    EQUALS_TO = 'equals_to'  # Type 1: SSO releases a single-value attribute with an exact value that matches
    CONTAINS = 'contains'  # Type 2: SSO releases a multi-value attribute, of which one value matches
    IN = 'in'  # Type 3: SSO releases a single-value attribute that have multiple valid values


class InstitutionManager(models.Manager):

    def get_queryset(self):
        return super().get_queryset().filter(deactivated__isnull=True)

    def get_all_institutions(self):
        return super().get_queryset()


class Institution(DirtyFieldsMixin, Loggable, ObjectIDMixin, BaseModel, GuardianMixin):
    objects = InstitutionManager()

    # TODO Remove null=True for things that shouldn't be nullable
    # e.g. CharFields should never be null=True

    INSTITUTION_GROUPS = {
        'institutional_admins': ('view_institutional_metrics',),
    }
    group_format = 'institution_{self._id}_{group}'
    groups = INSTITUTION_GROUPS

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default='', null=True)

    # Institution integration type
    delegation_protocol = models.CharField(
        choices=[(type.value, type.name) for type in IntegrationType],
        max_length=15,
        blank=True,
        default=''
    )

    # Default Storage Region
    storage_regions = models.ManyToManyField(
        'addons_osfstorage.Region',
        through=InstitutionStorageRegion,
        related_name='institutions'
    )

    # Verified employment/education affiliation source for `via-orcid` institutions
    orcid_record_verified_source = models.CharField(max_length=255, blank=True, default='')

    # login_url and logout_url can be null or empty
    login_url = models.URLField(null=True, blank=True)
    logout_url = models.URLField(null=True, blank=True)

    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True, null=True, blank=True)
    support_email = LowercaseEmailField(default='', blank=True, validators=[validate_email])

    contributors = models.ManyToManyField(
        django_conf_settings.AUTH_USER_MODEL,
        through=InstitutionalContributor,
        related_name='institutions'
    )

    is_deleted = models.BooleanField(default=False, db_index=True)
    deleted = NonNaiveDateTimeField(null=True, blank=True)
    deactivated = NonNaiveDateTimeField(null=True, blank=True)
    ror_uri = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='The full URI for the this institutions ROR.'
    )
    identifier_domain = models.URLField(
        max_length=500,
        null=True,
        blank=True,
        help_text='The full domain this institutions that will appear in DOI metadata.'
    )

    class Meta:
        # custom permissions for use in the OSF Admin App
        permissions = (
            # Clashes with built-in permissions
            # ('view_institution', 'Can view institution details'),
            ('view_institutional_metrics', 'Can access metrics endpoints for their Institution'),
        )

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super().__init__(*args, **kwargs)

    def __unicode__(self):
        return f'{self.name} : ({self._id})'

    def __str__(self):
        return f'{self.name} : ({self._id})'

    @property
    def api_v2_url(self):
        return reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def absolute_url(self):
        return urljoin(website_settings.DOMAIN, f'institutions/{self._id}/')

    @property
    def absolute_api_v2_url(self):
        from api.base.utils import absolute_reverse
        return absolute_reverse('institutions:institution-detail', kwargs={'institution_id': self._id, 'version': 'v2'})

    @property
    def nodes_url(self):
        return self.absolute_api_v2_url + 'nodes/'

    @property
    def nodes_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/nodes/'

    @property
    def registrations_url(self):
        return self.absolute_api_v2_url + 'registrations/'

    @property
    def registrations_relationship_url(self):
        return self.absolute_api_v2_url + 'relationships/registrations/'

    @property
    def logo_path(self):
        try:
            return self.asset_files.get(name='logo').file.url
        except InstitutionAssetFile.DoesNotExist:
            return '/static/img/institutions/shields/placeholder-shield.png'

    @property
    def logo_path_rounded_corners(self):
        try:
            return self.asset_files.get(name='logo_rounded_corners').file.url
        except InstitutionAssetFile.DoesNotExist:
            return '/static/img/institutions/shields-rounded-corners/placeholder-shield-rounded-corners.png'

    @property
    def banner_path(self):
        try:
            return self.asset_files.get(name='banner').file.url
        except InstitutionAssetFile.DoesNotExist:
            return '/static/img/institutions/banners/placeholder-banner.png'

    def update_search(self):
        from website.search.search import update_institution
        from website.search.exceptions import SearchUnavailableError

        try:
            update_institution(self)
        except SearchUnavailableError as e:
            logger.exception(e)

        for node in self.nodes.filter(is_deleted=False):
            node.update_search()

    def save(self, *args, **kwargs):
        saved_fields = self.get_dirty_fields()
        super().save(*args, **kwargs)
        if saved_fields:
            self.update_search()

    def _send_deactivation_email(self):
        """Send notification emails to all users affiliated with the deactivated institution.
        """
        forgot_password = 'forgotpassword' if website_settings.DOMAIN.endswith('/') else '/forgotpassword'
        attempts = 0
        success = 0
        for user in self.get_institution_users():
            try:
                attempts += 1
                mails.send_mail(
                    to_addr=user.username,
                    mail=mails.INSTITUTION_DEACTIVATION,
                    user=user,
                    forgot_password_link=f'{website_settings.DOMAIN}{forgot_password}',
                    osf_support_email=website_settings.OSF_SUPPORT_EMAIL
                )
            except Exception as e:
                logger.error(f'Failed to send institution deactivation email to user [{user._id}] at [{self._id}]')
                sentry.log_exception(e)
                continue
            else:
                success += 1
        logger.info(f'Institution deactivation notification email has been '
                    f'sent to [{success}/{attempts}] users for [{self._id}]')

    def deactivate(self):
        """Deactivate an active institution, update OSF search and send emails to all affiliated users.
        """
        if not self.deactivated:
            self.deactivated = timezone.now()
            self.save()
            # Django mangers aren't used when querying on related models. Thus, we can query
            # affiliated users and send notification emails after the institution has been deactivated.
            self._send_deactivation_email()
        else:
            message = f'Action rejected - deactivating an inactive institution [{self._id}].'
            logger.warning(message)
            sentry.log_message(message)

    def reactivate(self):
        """Reactivate an inactive institution and update OSF search without sending out emails.
        """
        if self.deactivated:
            self.deactivated = None
            self.save()
        else:
            message = f'Action rejected - reactivating an active institution [{self._id}].'
            logger.warning(message)
            sentry.log_message(message)

    def get_institution_users(self):
        from .user import OSFUser
        qs = InstitutionAffiliation.objects.filter(institution__id=self.id).values_list('user', flat=True)
        return OSFUser.objects.filter(pk__in=qs)

    def get_semantic_iri(self) -> str:
        if self.ror_uri:  # prefer ROR if we have it
            return self.ror_uri
        if self.identifier_domain:  # if not ROR, at least URI
            return self.identifier_domain
        # fallback to a url on osf
        return self.absolute_url

    def get_semantic_iris(self) -> Iterable[str]:
        yield from super().get_semantic_iris()
        yield from filter(bool, [
            self.ror_uri,
            self.identifier_domain,
            self.absolute_url,
        ])


@receiver(post_save, sender=Institution)
def create_institution_auth_groups(sender, instance, created, **kwargs):
    if created:
        instance.update_group_permissions()
