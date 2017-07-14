from rest_framework.exceptions import ValidationError, PermissionDenied

from api.cas import messages

from osf.models import ApiOAuth2Application, ApiOAuth2PersonalToken, ApiOAuth2Scope, Institution, OSFUser


def get_oauth_token(body_data):
    """ Get the owner and scopes of a personal access token by token id.
    """

    service_type = body_data.get('serviceType')
    token_id = body_data.get('tokenId')

    if service_type != 'OAUTH_TOKEN' or not token_id:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    try:
        token = ApiOAuth2PersonalToken.objects.get(token_id=token_id)
    except ApiOAuth2PersonalToken.DoesNotExist:
        raise PermissionDenied(detail=messages.TOKEN_NOT_FOUND)

    try:
        user = OSFUser.objects.get(pk=token.owner_id)
    except OSFUser.DoesNotExist:
        raise PermissionDenied(detail=messages.TOKEN_OWNER_NOT_FOUND)

    return {
        'tokenId': token.token_id,
        'ownerId': user._id,
        'tokenScopes': token.scopes,
    }


def get_oauth_scope(body_data):
    """ Get the description of the oauth scope by scope name.
    """

    service_type = body_data.get('serviceType')
    scope_name = body_data.get('scopeName')

    if service_type != 'OAUTH_SCOPE' or not scope_name:
        raise ValidationError(detail=messages.INVALID_REQUEST)

    try:
        scope = ApiOAuth2Scope.objects.get(name=scope_name)
        if not scope.is_active:
            raise PermissionDenied(detail=messages.SCOPE_NOT_ACTIVE)
    except ApiOAuth2Scope.DoesNotExist:
        raise PermissionDenied(detail=messages.SCOPE_NOT_FOUND)

    return {
        'scopeDescription': scope.description,
    }


def load_oauth_apps(body_data):
    """ Load all active developer applications.
    """

    service_type = body_data.get('serviceType')
    if service_type != 'OAUTH_APPS':
        raise ValidationError(detail=messages.INVALID_REQUEST)

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


def load_institutions(body_data):
    """ Load institutions that provide authentication delegation.
    """

    service_type = body_data.get('serviceType')

    if service_type != 'INSTITUTIONS':
        raise ValidationError(detail=messages.INVALID_REQUEST)

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
