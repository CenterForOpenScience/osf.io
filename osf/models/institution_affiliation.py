from django.db import models

from osf.models.base import BaseModel
from osf.models.validators import validate_email
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField
from osf.utils.fields import LowercaseEmailField


class InstitutionAffiliation(BaseModel):

    DEFAULT_IDENTITY_VALUE_FROM_MIGRATION = 'NOT_AVAILABLE'

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

    @classmethod
    def create(cls, user, institution, sso_identity=None, sso_mail=None, sso_department=None, is_migration=False):
        if is_migration:
            sso_identity = cls.DEFAULT_IDENTITY_VALUE_FROM_MIGRATION
            sso_mail = None
        affiliation = cls(
            user=user,
            institution=institution,
            sso_identity=sso_identity,
            sso_mail=sso_mail,
            sso_department=sso_department,
            sso_other_attributes={},
        )
        affiliation.save()
        return affiliation

    @classmethod
    def add_multiple(cls, user, institutions):
        for institution in institutions:
            if not user.is_affiliated_with_institution(institution):
                InstitutionAffiliation.create(user, institution)
