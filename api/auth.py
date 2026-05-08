from django.views.decorators.http import require_GET
from django.http import HttpResponseRedirect, HttpResponse
from furl import furl
from website import settings
from framework.auth import cas
from framework.auth.utils import print_cas_log, LogLevel

def make_response_from_ticket(ticket, service_url):
    """
    Given a CAS ticket and service URL, attempt to validate the user and return user object.

    :param str ticket: CAS service ticket
    :param str service_url: Service URL from which the authentication request originates
    :return: user object if authentication is successful, otherwise an HttpResponse with an error message and status code
    """

    service_furl = furl(service_url)
    if 'ticket' in service_furl.args:
        service_furl.remove(args=['ticket'])
    client = cas.get_client()
    cas_resp = client.service_validate(ticket, service_furl.url)
    if cas_resp.authenticated:
        user, external_credential, action = cas.get_user_from_cas_resp(cas_resp)
        if user and action == 'authenticate':
            print_cas_log(
                f'CAS response - authenticating user: user=[{user._id}], '
                f'external=[{external_credential}], action=[{action}]',
                LogLevel.INFO,
            )
            # if user is authenticated by CAS
            print_cas_log(f'CAS response - finalizing authentication: user=[{user._id}]', LogLevel.INFO)
            return user

    return HttpResponse('CAS authentication failed', status=401)

@require_GET
def auth_login(request):
    ticket = request.GET.get('ticket')
    if not ticket:
        return HttpResponse('Missing ticket', status=400)

    # redirect to Angular
    next_url = request.GET.get('next', 'http://localhost:4200/')
    response = HttpResponseRedirect(next_url)

    from osf.utils.fields import ensure_str
    from django.contrib.auth import login
    import itsdangerous

    service_url = furl(request.build_absolute_uri()).remove(args=['ticket'])
    user_or_response = make_response_from_ticket(ticket, service_url.url)
    if isinstance(user_or_response, HttpResponse):
        return user_or_response
    login(request, user_or_response, backend='api.base.authentication.backends.ODMBackend')
    session = request.session
    data = {
        'auth_user_username': user_or_response.username,
        'auth_user_id': user_or_response._primary_key,
        'auth_user_fullname': user_or_response.fullname,
        'user_reference_uri': user_or_response.get_semantic_iri(),
    }
    for key, value in data.items() if data else {}:
        session[key] = value

    # Note: session.modified is set to False here to prevent Django from saving the session again in SessionMiddleware.process_response,
    # which would overwrite the session cookie set here with an unsigned version.
    # Setting cookie can be done in process_response by adding session_key signing.
    session.modified = False
    session.save()

    session_key = session._get_or_create_session_key()
    signed_session_key = ensure_str(itsdangerous.Signer(settings.SECRET_KEY).sign(session_key))

    response.set_cookie(
        'osf',
        signed_session_key,
        domain=settings.OSF_COOKIE_DOMAIN,
        secure=settings.SESSION_COOKIE_SECURE,
        httponly=settings.SESSION_COOKIE_HTTPONLY,
        samesite=settings.SESSION_COOKIE_SAMESITE,
    )
    from django.middleware.csrf import get_token

    csrf_token = get_token(request)

    response.set_cookie(
        'api-csrf',
        csrf_token,
        samesite='Lax',
    )

    return response
