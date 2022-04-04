"""Factories for the My Screen addon."""
import factory
from factory.django import DjangoModelFactory
from osf_tests.factories import UserFactory, ProjectFactory

from ..models import UserSettings, NodeSettings


def make_binderhub(
    binderhub_url='https://test.binderhub.my.site',
    binderhub_oauth_client_id='TEST_CLIENT_BH',
    binderhub_oauth_client_secret='TEST_SECRET_BH',
    binderhub_oauth_authorize_url='https://test.binderhub.my.site/authorize',
    binderhub_oauth_token_url='https://test.binderhub.my.site/token',
    binderhub_oauth_scope=['identity'],
    binderhub_services_url='https://test.binderhub.my.site',
    jupyterhub_url='https://test.jupyterhub.my.site',
    jupyterhub_oauth_client_id='TEST_CLIENT_JH',
    jupyterhub_oauth_client_secret='TEST_SECRET_JH',
    jupyterhub_oauth_authorize_url='https://test.jupyterhub.my.site/authorize',
    jupyterhub_oauth_token_url='https://test.jupyterhub.my.site/token',
    jupyterhub_oauth_scope=['identity'],
    jupyterhub_api_url='https://test.jupyterhub.my.site/api',
    jupyterhub_admin_api_token='TEST_ADMIN_JH',
):
    return {
        'binderhub_url': binderhub_url,
        'binderhub_oauth_client_id': binderhub_oauth_client_id,
        'binderhub_oauth_client_secret': binderhub_oauth_client_secret,
        'binderhub_oauth_authorize_url': binderhub_oauth_authorize_url,
        'binderhub_oauth_token_url': binderhub_oauth_token_url,
        'binderhub_oauth_scope': binderhub_oauth_scope,
        'binderhub_services_url': binderhub_services_url,
        'jupyterhub_url': jupyterhub_url,
        'jupyterhub_oauth_client_id': jupyterhub_oauth_client_id,
        'jupyterhub_oauth_client_secret': jupyterhub_oauth_client_secret,
        'jupyterhub_oauth_authorize_url': jupyterhub_oauth_authorize_url,
        'jupyterhub_oauth_token_url': jupyterhub_oauth_token_url,
        'jupyterhub_oauth_scope': jupyterhub_oauth_scope,
        'jupyterhub_api_url': jupyterhub_api_url,
        'jupyterhub_admin_api_token': jupyterhub_admin_api_token,
    }

class UserSettingsFactory(DjangoModelFactory):
    class Meta:
        model = UserSettings

    owner = factory.SubFactory(UserFactory)

class NodeSettingsFactory(DjangoModelFactory):
    class Meta:
        model = NodeSettings

    owner = factory.SubFactory(ProjectFactory)
