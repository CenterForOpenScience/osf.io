import logging

from django.db import models

from osf.models import base

logger = logging.getLogger(__name__)


class InstitutionEntitlement(base.BaseModel):
    institution = models.ForeignKey('Institution', on_delete=models.CASCADE)
    entitlement = models.CharField(max_length=255)
    login_availability = models.BooleanField(default=True)
    modifier_id = models.ForeignKey('OSFUser', on_delete=models.CASCADE)

    class Meta:
        unique_together = ('institution', 'entitlement')

    def __init__(self, *args, **kwargs):
        kwargs.pop('node', None)
        super(InstitutionEntitlement, self).__init__(*args, **kwargs)

    def __unicode__(self):
        return u'institution_{}:{}'.format(self.institution._id, self.entitlement)
