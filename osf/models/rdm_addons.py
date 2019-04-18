# -*- coding: utf-8 -*-

from django.db import models
from osf.models.base import BaseModel, Guid
from osf.models import ExternalAccount, Institution, AbstractNode


class RdmAddonOption(BaseModel):
    provider = models.CharField(max_length=50, blank=False, null=False, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE)

    institution = models.ForeignKey(Institution, blank=False, null=False)
    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)

    class Meta:
        unique_together = (('provider', 'institution'),)

    def get_management_node_guid(self):
        if self.management_node:
            return self.management_node._id
        else:
            return None

    def set_management_node_by_guid(self, guid, save=False):
        guid_obj = Guid.objects.get(_id=guid)
        node = guid_obj.referent
        if not isinstance(node, AbstractNode):
            raise TypeError('"guid" must be a guid of AbstractNode.')

        self.management_node = node
        if save:
            self.save()

    def unset_management_node(self, save=True):
        self.management_node = None
        if save:
            self.save()


class RdmAddonNoInstitutionOption(BaseModel):
    provider = models.CharField(max_length=50, blank=False, null=False, unique=True, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE)

    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)
