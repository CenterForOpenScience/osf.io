from django.contrib.postgres import fields
from django.db import models
from django.conf import settings


from osf_models import models as osf_models_models
from osf_models.exceptions import UserNotAffiliatedError
from osf_models.models import NodeLog
from osf_models.models.mixins import Loggable
from osf_models.utils.auth import Auth


class Institution(Loggable, osf_models_models.base.GuidMixin, osf_models_models.base.BaseModel):
    auth_url = models.URLField()
    logout_url = models.URLField()
    domains = fields.ArrayField(models.CharField(max_length=255), db_index=True)
    logo_name = models.CharField(max_length=255)  # TODO: Could this be a FilePathField?
    email_domains = fields.ArrayField(models.CharField(max_length=255), db_index=True)
    banner_name = models.CharField(max_length=255)

    contributors = models.ManyToManyField(settings.AUTH_USER_MODEL,
                                          through=osf_models_models.Contributor,
                                          related_name='contributed_to')

    affiliated_institutions = models.ManyToManyField('Node', related_name='affiliated_intitutions')


    def add_affiliated_intitution(self, inst, user, save=False, log=True):
        if not user.is_affiliated_with_institution(inst):
            raise UserNotAffiliatedError('User is not affiliated with {}'.format(inst.name))
        if inst not in self.affiliated_institutions:
            self.affiliated_institutions.add(inst)
        if log:
            self.add_log(
                action=NodeLog.AFFLILIATED_INSTITUTION_ADDED,
                params={
                    'node': self._primary_key,
                    'institution': {
                        'id': inst._id,
                        'name': inst.name
                    }
                },
                auth=Auth(user)
            )
