from api.base import exceptions as api_exception

from osf.models import ApiOAuth2Application, ApiOAuth2PersonalToken, ApiOAuth2Scope, Institution, OSFUser


def get_oauth_token(data):
    """
    Get the owner and scopes of a personal access token by token id.

    :param data: the request data
    :return: the response body
    :raises: MalformedRequestError, OauthPersonalAccessTokenError
    """
    token_id = data.get('tokenId')

    if not token_id:
        raise api_exception.MalformedRequestError

    try:
        token = ApiOAuth2PersonalToken.objects.filter(token_id=token_id).get()
    except ApiOAuth2PersonalToken.DoesNotExist:
        raise api_exception.OauthPersonalAccessTokenError

    try:
        user = OSFUser.objects.filter(pk=token.owner_id).get()
    except OSFUser.DoesNotExist:
        raise api_exception.OauthPersonalAccessTokenError

    return {
        'tokenId': token.token_id,
        'ownerId': user._id,
        'tokenScopes': token.scopes,
    }


def get_oauth_scope(data):
    """
    Get the description of the oauth scope by scope name.

    :param data: the request data
    :return: the response body
    :raises: MalformedRequestError, OauthScopeError
    """

    scope_name = data.get('scopeName')

    if not scope_name:
        raise api_exception.MalformedRequestError

    try:
        scope = ApiOAuth2Scope.objects.get(name=scope_name)
        if not scope.is_active:
            raise api_exception.OauthScopeError
    except ApiOAuth2Scope.DoesNotExist:
            raise api_exception.OauthScopeError

    return {
        'scopeDescription': scope.description,
    }


def load_oauth_apps():
    """ Load all active developer applications.
    """

    oauth_applications = ApiOAuth2Application.objects.filter(is_active=True)

    content = {}
    for oauth_app in oauth_applications:
        key = oauth_app._id
        value = {
            'name': oauth_app.name,
            'description': oauth_app.description,
            'callbackUrl': oauth_app.callback_url,
            'clientId': oauth_app.client_id,
            'clientSecret': oauth_app.client_secret,
        }
        content.update({key: value})

    return content


def load_institutions():
    """ Load institutions that provide authentication delegation.
    """

    institutions = Institution.objects \
        .exclude(delegation_protocol__isnull=True) \
        .exclude(delegation_protocol__exact='')

    content = {}
    for institution in institutions:
        key = institution._id
        value = {
            'institutionName': institution.name,
            'institutionLoginUrl': institution.login_url if institution.login_url else '',
            'institutionLogoutUrl': institution.logout_url,
            'delegationProtocol': institution.delegation_protocol,
        }
        content.update({key: value})

    return content
