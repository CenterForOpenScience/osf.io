import logging

from django.db import models

from framework import sentry

from .base import BaseModel
from .validators import validate_email
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import LowercaseEmailField
from osf.exceptions import InstitutionAffiliationStateError


logger = logging.getLogger(__name__)


class InstitutionAffiliation(BaseModel):

    DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE = 'SSO_IDENTITY_NOT_AVAILABLE'

    user = models.ForeignKey('OSFUser', on_delete=models.CASCADE)
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)

    sso_identity = models.CharField(default='', null=True, blank=True, max_length=255)
    sso_mail = LowercaseEmailField(default='', null=True, blank=True, validators=[validate_email])
    sso_department = models.CharField(default='', null=True, blank=True, max_length=255)

    sso_other_attributes = DateTimeAwareJSONField(default=dict, null=False, blank=True)

    class Meta:
        unique_together = ('user', 'institution')

    def __repr__(self):
        return f'<{self.__class__.__name__}(user={self.user._id}, institution={self.institution._id}, ' \
               f'identity={self.sso_identity}, mail={self.sso_mail}, department={self.sso_department}>'

    def __str__(self):
        return f'{self.user._id}::{self.institution._id}::{self.sso_identity}'


def get_user_by_institution_identity(institution, sso_identity):
    """Return the user with the given sso_identity for the given institution if found. Return ``None`` if missing
    inputs or if user not found. Raise exception if multiple users found. In addition, returns a second value which
    determines whether the sso_identity is an eligible identity.
    """
    if not institution or not sso_identity:
        return None, False
    # Skip the default identity that is used only for institutions that don't have SSO
    if sso_identity == InstitutionAffiliation.DEFAULT_VALUE_FOR_SSO_IDENTITY_NOT_AVAILABLE:
        return None, False
    try:
        affiliation = InstitutionAffiliation.objects.get(institution___id=institution._id, sso_identity=sso_identity)
    except InstitutionAffiliation.DoesNotExist:
        return None, True
    except InstitutionAffiliation.MultipleObjectsReturned as err:
        message = f'Duplicate SSO Identity: institution={institution._id}, sso_identity={sso_identity}, err={str(err)}'
        logger.error(message)
        sentry.log_message(message)
        raise InstitutionAffiliationStateError(message)
    return affiliation.user, True
