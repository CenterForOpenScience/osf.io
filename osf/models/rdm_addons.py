# -*- coding: utf-8 -*-

from django.db import models

from osf.models.base import BaseModel
from osf.models import Institution, AbstractNode
from osf.models.external import ExternalAccount
from osf.utils.datetime_aware_jsonfield import DateTimeAwareJSONField

# see admin.rdm_addons.utils.get_rdm_addon_option

class CommonMixin(object):
    def get_one_external_account(self):
        if not self.external_accounts.exists():
            return None
        return self.external_accounts.first().oauth_key


class RdmAddonOption(BaseModel, CommonMixin):
    provider = models.CharField(max_length=50, blank=False, null=False, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                        related_name='management_rdm_addon_option_set')
    organizational_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                            related_name='organizational_rdm_addon_option_set')

    institution = models.ForeignKey(Institution, blank=False, null=False)
    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)

    extended = DateTimeAwareJSONField(default=dict, blank=True)

    class Meta:
        unique_together = (('provider', 'institution'),)


class RdmAddonNoInstitutionOption(BaseModel, CommonMixin):
    provider = models.CharField(max_length=50, blank=False, null=False, unique=True, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                        related_name='management_rdm_addon_no_institution_option_set')
    organizational_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE,
                                            related_name='organizational_rdm_addon_no_institution_option_set')

    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)
