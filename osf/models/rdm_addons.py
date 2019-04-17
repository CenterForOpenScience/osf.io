# -*- coding: utf-8 -*-

from django.db import models
from osf.models.base import BaseModel
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

class RdmAddonNoInstitutionOption(BaseModel):
    provider = models.CharField(max_length=50, blank=False, null=False, unique=True, db_index=True)
    is_forced = models.BooleanField(default=False)
    is_allowed = models.BooleanField(default=True)
    management_node = models.ForeignKey(AbstractNode, blank=True, null=True, default=None, on_delete=models.CASCADE)

    external_accounts = models.ManyToManyField(ExternalAccount, blank=True)
