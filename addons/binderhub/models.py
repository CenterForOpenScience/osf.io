import json
import logging

from osf.models.base import BaseModel
from osf.models.user import OSFUser
from osf.models.node import AbstractNode
from addons.base.models import BaseNodeSettings, BaseUserSettings
from django.db import models
from osf.utils.fields import EncryptedTextField
from . import settings

logger = logging.getLogger(__name__)


def get_default_binderhubs(allow_secrets=False):
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
        return [binderhub]
    binderhub.update({
        'binderhub_oauth_client_secret': binderhub_oauth['client_secret'],
        'jupyterhub_oauth_client_secret': jupyterhub_oauth['client_secret'],
        'jupyterhub_admin_api_token': jupyterhub_oauth['admin_api_token'],
    })
    return [binderhub]

def _fill_binderhub_secret(binderhub, binderhubs_list):
    if 'binderhub_oauth_client_secret' in binderhub and 'jupyterhub_oauth_client_secret' in binderhub and 'jupyterhub_admin_api_token' in binderhub:
        return binderhub.copy()
    flattened_binderhubs_list = sum(binderhubs_list, [])
    template_binderhubs = [b for b in flattened_binderhubs_list if b['binderhub_url'] == binderhub['binderhub_url']]
    if len(template_binderhubs) == 0:
        raise KeyError('BinderHub not found: ' + binderhub['binderhub_url'])
    template_binderhub = template_binderhubs[0]
    r = binderhub.copy()
    r['binderhub_oauth_client_secret'] = template_binderhub['binderhub_oauth_client_secret']
    r['jupyterhub_oauth_client_secret'] = template_binderhub['jupyterhub_oauth_client_secret']
    r['jupyterhub_admin_api_token'] = template_binderhub['jupyterhub_admin_api_token']
    return r

def fill_binderhub_secrets(target_binderhubs, binderhubs_list):
    return [_fill_binderhub_secret(binderhub, binderhubs_list) for binderhub in target_binderhubs]

def _verify_binderhubs(binderhubs):
    urls = set([b['binderhub_url'] for b in binderhubs])
    for url in urls:
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
            return get_default_binderhubs(allow_secrets=allow_secrets)
        r = json.loads(self.available_binderhubs)
        if len(r) == 0:
            return get_default_binderhubs(allow_secrets=allow_secrets)
        if allow_secrets:
            return r
        for hub in r:
            _remove_secret(hub)
        return r

    def set_available_binderhubs(self, available_binderhubs):
        _verify_binderhubs(available_binderhubs)
        self.available_binderhubs = json.dumps(available_binderhubs)
        self.save()

    @property
    def complete(self):
        return True
