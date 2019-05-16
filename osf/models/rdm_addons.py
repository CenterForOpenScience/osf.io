# -*- coding: utf-8 -*-

from django.db import models
from django.db.models.signals import post_save
from django.dispatch import receiver

from addons.googledrive.apps import GoogleDriveAddonConfig
from addons.iqbrims.utils import copy_node_auth
from website import settings as website_settings
from addons.iqbrims.apps import IQBRIMSAddonConfig
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


@receiver(post_save, sender=RdmAddonOption)
def add_iqbrims_addon_to_affiliating_nodes(sender, instance, created, **kwargs):
    addon_short_name = IQBRIMSAddonConfig.short_name
    if addon_short_name not in website_settings.ADDONS_AVAILABLE_DICT:
        return

    if instance.is_allowed and instance.management_node is not None:
        nodes = AbstractNode.find_by_institutions(instance.institution)
        for node in nodes:
            node.add_addon(addon_short_name, auth=None, log=False)

            # copy auth if node has copy addon
            if GoogleDriveAddonConfig.short_name not in website_settings.ADDONS_AVAILABLE_DICT:
                return
            copy_node_addon = node.get_addon(GoogleDriveAddonConfig.short_name)
            if copy_node_addon is not None:
                copy_node_auth(node, copy_node_addon)
