import json
import logging
import re

from osf.models.base import BaseModel
from osf.models.user import OSFUser
from osf.models.node import AbstractNode
from addons.base.models import BaseNodeSettings, BaseUserSettings
from django.db import models
from osf.utils.fields import EncryptedTextField
from . import settings

logger = logging.getLogger(__name__)


def camel_to_snake(name: str) -> str:
    return re.sub(r'([a-z0-9])([A-Z])', r'\1_\2', name).lower()

def get_default_binderhub(allow_secrets=False):
    binderhub_oauth = settings.BINDERHUB_OAUTH_CLIENT
    jupyterhub_url, jupyterhub_oauth = list(settings.JUPYTERHUB_OAUTH_CLIENTS.items())[0]
    binderhub = {
        'binderhub_url': settings.DEFAULT_BINDER_URL,
        'binderhub_oauth_client_id': binderhub_oauth['client_id'],
        'binderhub_oauth_authorize_url': binderhub_oauth['authorize_url'],
        'binderhub_oauth_token_url': binderhub_oauth['token_url'],
        'binderhub_oauth_scope': binderhub_oauth['scope'],
        'binderhub_services_url': binderhub_oauth['services_url'],
        'jupyterhub_url': jupyterhub_url,
        'jupyterhub_oauth_client_id': jupyterhub_oauth['client_id'],
        'jupyterhub_oauth_authorize_url': jupyterhub_oauth['authorize_url'],
        'jupyterhub_oauth_token_url': jupyterhub_oauth['token_url'],
        'jupyterhub_oauth_scope': jupyterhub_oauth['scope'],
        'jupyterhub_api_url': jupyterhub_oauth['api_url'],
        'jupyterhub_max_servers': jupyterhub_oauth['max_servers'] if 'max_servers' in jupyterhub_oauth else None,
        'jupyterhub_logout_url': jupyterhub_oauth['logout_url'] if 'logout_url' in jupyterhub_oauth else None,
    }
    if not allow_secrets:
        return binderhub
    binderhub.update({
        'binderhub_oauth_client_secret': binderhub_oauth['client_secret'],
        'jupyterhub_oauth_client_secret': jupyterhub_oauth['client_secret'],
        'jupyterhub_admin_api_token': jupyterhub_oauth['admin_api_token'],
    })
    return binderhub

def _fill_binderhub_secret(binderhub, binderhub_list):
    if 'binderhub_oauth_client_secret' in binderhub and 'jupyterhub_oauth_client_secret' in binderhub and 'jupyterhub_admin_api_token' in binderhub:
        return binderhub.copy()
    template_binderhubs = [b for b in binderhub_list if b['binderhub_url'] == binderhub['binderhub_url']]
    if len(template_binderhubs) == 0:
        raise KeyError('BinderHub not found: ' + binderhub['binderhub_url'])
    template_binderhub = template_binderhubs[0]
    r = binderhub.copy()
    r['binderhub_oauth_client_secret'] = template_binderhub['binderhub_oauth_client_secret']
    r['jupyterhub_oauth_client_secret'] = template_binderhub['jupyterhub_oauth_client_secret']
    r['jupyterhub_admin_api_token'] = template_binderhub['jupyterhub_admin_api_token']
    return r

def fill_binderhub_secrets(target_binderhubs, binderhubs_list):
    binderhub_list = sum(binderhubs_list, [])
    return [
        _fill_binderhub_secret(binderhub, binderhub_list)
        for binderhub in target_binderhubs
    ]

def _verify_binderhubs(binderhubs):
    for url in set([b['binderhub_url'] for b in binderhubs]):
        matched = [b for b in binderhubs if b['binderhub_url'] == url]
        assert len(matched) == 1, url
    for binderhub in binderhubs:
        _verify_binderhub(binderhub)

def _verify_binderhub(binderhub):
    assert 'binderhub_url' in binderhub, binderhub
    assert 'binderhub_oauth_client_id' in binderhub, binderhub
    assert 'binderhub_oauth_client_secret' in binderhub, binderhub
    assert 'binderhub_oauth_authorize_url' in binderhub, binderhub
    assert 'binderhub_oauth_token_url' in binderhub, binderhub
    assert 'binderhub_oauth_scope' in binderhub, binderhub
    assert 'binderhub_services_url' in binderhub, binderhub
    assert 'jupyterhub_url' in binderhub, binderhub
    assert 'jupyterhub_oauth_client_id' in binderhub, binderhub
    assert 'jupyterhub_oauth_client_secret' in binderhub, binderhub
    assert 'jupyterhub_oauth_authorize_url' in binderhub, binderhub
    assert 'jupyterhub_oauth_token_url' in binderhub, binderhub
    assert 'jupyterhub_oauth_scope' in binderhub, binderhub
    assert 'jupyterhub_api_url' in binderhub, binderhub
    assert 'jupyterhub_admin_api_token' in binderhub, binderhub

def _remove_secret(binderhub):
    del binderhub['binderhub_oauth_client_secret']
    del binderhub['jupyterhub_oauth_client_secret']
    del binderhub['jupyterhub_admin_api_token']


class BinderHubToken(BaseModel):
    user = models.ForeignKey(OSFUser, related_name='binderhub_token', db_index=True,
                             null=True, blank=True, on_delete=models.CASCADE)

    node = models.ForeignKey(AbstractNode, related_name='binderhub_token',
                             db_index=True, null=True, blank=True, on_delete=models.CASCADE)

    binderhub_url = models.TextField(blank=True, null=True)

    binderhub_token = models.TextField(blank=True, null=True)

    jupyterhub_url = models.TextField(blank=True, null=True)

    jupyterhub_token = models.TextField(blank=True, null=True)


class ServerAnnotation(BaseModel):
    user = models.ForeignKey(OSFUser, db_index=True, null=True,
                             blank=True, on_delete=models.CASCADE)

    node = models.ForeignKey(AbstractNode, db_index=True, null=True,
                             blank=True, on_delete=models.CASCADE)

    binderhub_url = models.TextField(blank=True, null=True)

    jupyterhub_url = models.TextField(blank=True, null=True)

    server_url = models.TextField(blank=False, null=False)

    name = models.TextField(blank=True, null=False)

    memotext = models.TextField(blank=True, null=False)

    def make_resource_object(self):
        return {
            'type': 'server-annotation',
            'id': self.id,
            'attributes': {
                'binderhubUrl': self.binderhub_url,
                'jupyterhubUrl': self.jupyterhub_url,
                'serverUrl': self.server_url,
                'name': self.name,
                'memotext': self.memotext
            }
        }

class InvalidUpdateDirectiveError(Exception):
    """Raised if an `update directive` given to CustomBaseImage is invalid."""
    pass

class CustomBaseImage(BaseModel):
    user = models.ForeignKey(OSFUser, db_index=True, null=True,
                             blank=True, on_delete=models.CASCADE)

    node = models.ForeignKey(AbstractNode, db_index=True, null=True,
                             blank=True, on_delete=models.CASCADE)

    name = models.TextField(blank=False, null=False)

    image_reference = models.TextField(blank=False, null=False)

    description_ja = models.TextField(blank=True, null=False)

    description_en = models.TextField(blank=True, null=False)

    deprecated = models.BooleanField(default=False)

    updatable_filed_names = ['name', 'description_ja', 'description_en', 'deprecated']

    @classmethod
    def is_valid_camel_update_directive(cls, update_directive):
        if not all((camel_to_snake(key) in cls.updatable_filed_names for key in update_directive.keys())):
            return False
        if 'name' in update_directive and not update_directive.get('name'):
            return False
        return True

    def safe_camel_update(self, update_directive):
        """
        Update the fields specified by `update_directive` and returns a
        dictionary that holds the old values of updated fields. The keys
        of returned dictionary are in *snake_case*, while the keys of
        `update_directive` must be in *camelCase*. The returned value is
        useful to rollback the model object on DB commit failure.

        Args:
            update_directive (dict): dictionary with camelCased keys

        Returns:
            dict: Old values of updated fields { field_name: old_value }
        """
        if not self.is_valid_camel_update_directive(update_directive):
            raise InvalidUpdateDirectiveError("Invalid update directive")

        changed_fields = {}

        for field_name, updated_value in update_directive.items():
            snake_case_field = camel_to_snake(field_name)
            current_value = getattr(self, snake_case_field, None)

            if current_value != updated_value:
                changed_fields[snake_case_field] = current_value
                setattr(self, snake_case_field, updated_value)

        return changed_fields

    def make_resource_object(self, ancestor_level=0):
        return {
            'type': 'custom-base-image',
            'id': self.id,
            'attributes': {
                'name': self.name,
                'imageReference': self.image_reference,
                'descriptionJa': self.description_ja,
                'descriptionEn': self.description_en,
                'deprecated': self.deprecated,
                'guid': self.node._id,
                'nodeTitle': self.node.title,
                'level': ancestor_level,
            }
        }

class UserSettings(BaseUserSettings):
    binderhubs = EncryptedTextField(blank=True, null=True)

    def get_binderhubs(self, allow_secrets=False):
        if self.binderhubs is None or self.binderhubs == '':
            return []
        r = json.loads(self.binderhubs)
        if allow_secrets:
            return r
        for hub in r:
            _remove_secret(hub)
        return r

    def set_binderhubs(self, binderhubs):
        _verify_binderhubs(binderhubs)
        self.binderhubs = json.dumps(binderhubs)
        self.save()

    def remove_binderhub(self, binderhub_url):
        self.set_binderhubs(
            [
                b for b in self.get_binderhubs(True)
                if b['binderhub_url'] != binderhub_url
            ]
        )


class NodeSettings(BaseNodeSettings):
    binder_url = models.TextField(blank=True, null=True)

    available_binderhubs = EncryptedTextField(blank=True, null=True)

    user_settings = models.ForeignKey(UserSettings, null=True, blank=True, on_delete=models.CASCADE)

    def get_binder_url(self):
        if self.binder_url is None or self.binder_url == '':
            return settings.DEFAULT_BINDER_URL
        return self.binder_url

    def set_binder_url(self, binder_url):
        self.binder_url = binder_url
        self.save()

    def get_available_binderhubs(self, allow_secrets=False):
        if self.available_binderhubs is None or self.available_binderhubs == '':
            return [get_default_binderhub(allow_secrets=allow_secrets)]
        r = json.loads(self.available_binderhubs)
        if len(r) == 0:
            return [get_default_binderhub(allow_secrets=allow_secrets)]
        if allow_secrets:
            return r
        for hub in r:
            _remove_secret(hub)
        return r

    def set_available_binderhubs(self, available_binderhubs):
        _verify_binderhubs(available_binderhubs)
        self.available_binderhubs = json.dumps(available_binderhubs)
        self.save()

    def remove_binderhub(self, binderhub_url):
        self.set_available_binderhubs(
            [
                b for b in self.get_available_binderhubs(True)
                if b['binderhub_url'] != binderhub_url
            ]
        )

    def after_fork(self, original_node, forked_node, user, save=True):
        for img in CustomBaseImage.objects.filter(user=user, node=original_node):
            CustomBaseImage(
                user=user,
                node=forked_node,
                name=img.name,
                image_reference=img.image_reference,
                description_ja=img.description_ja,
                description_en=img.description_en,
                deprecated=img.deprecated,
            ).save()

    def after_template(self, templ_node, new_node, user, save=True):
        for img in CustomBaseImage.objects.filter(user=user, node=templ_node):
            CustomBaseImage(
                user=user,
                node=new_node,
                name=img.name,
                image_reference=img.image_reference,
                description_ja=img.description_ja,
                description_en=img.description_en,
                deprecated=img.deprecated,
            ).save()

    @property
    def complete(self):
        return True
