from django.views.decorators.http import require_GET
from django.http import HttpResponseRedirect, HttpResponse
from furl import furl
from framework.auth.tasks import update_user_from_activity
from framework.celery_tasks.handlers import enqueue_task
from framework.auth import cas
from framework.auth.utils import print_cas_log, LogLevel
from django.conf import settings as api_settings
from django.utils import timezone

def make_response_from_ticket(ticket, service_url):
    """
    Given a CAS ticket and service URL, attempt to validate the user and return a proper redirect response.

    :param str ticket: CAS service ticket
    :param str service_url: Service URL from which the authentication request originates
    :return: redirect response
    """

    service_furl = furl(service_url)
    # `service_url` is guaranteed to be removed of `ticket` parameter, which has been pulled off in
    # `framework.sessions.before_request()`.
    if 'ticket' in service_furl.args:
        service_furl.remove(args=['ticket'])
    client = cas.get_client()
    cas_resp = client.service_validate(ticket, service_furl.url)
    if cas_resp.authenticated:
        user, external_credential, action = cas.get_user_from_cas_resp(cas_resp)
        user_updates = {}  # serialize updates to user to be applied async
        session_updates = {}  # session updates to be applied immediately
        # user found and authenticated
        if user and action == 'authenticate':
            print_cas_log(
                f'CAS response - authenticating user: user=[{user._id}], '
                f'external=[{external_credential}], action=[{action}]',
                LogLevel.INFO,
            )
            # If users check the TOS consent checkbox via CAS, CAS sets the attribute `termsOfServiceChecked` to `true`
            # and then release it to OSF among other authentication attributes. When OSF receives it, it trusts CAS and
            # updates the user object if this is THE FINAL STEP of the login flow. DON'T update TOS consent status when
            # `external_credential == true` (i.e. w/ `action == 'authenticate'` or `action == 'external_first_login'`)
            # since neither is the final step of a login flow.
            tos_checked_via_cas = cas_resp.attributes.get('termsOfServiceChecked', 'false') == 'true'
            if tos_checked_via_cas:
                user_updates['accepted_terms_of_service'] = timezone.now()
                print_cas_log(f'CAS TOS consent checked: {user.guids.first()._id}, {user.username}', LogLevel.INFO)
            # if we successfully authenticate and a verification key is present, invalidate it
            if user.verification_key:
                user_updates['verification_key'] = None

            # if user is authenticated by external IDP, ask CAS to authenticate user for a second time
            # this extra step will guarantee that 2FA are enforced
            # current CAS session created by external login must be cleared first before authentication
            if external_credential:
                user.verification_key = cas.generate_verification_key()
                user.save()
                print_cas_log(
                    f'CAS response - redirect existing external IdP login to verification key login: user=[{user._id}]',
                    LogLevel.INFO,
                )
                return user, user_updates, session_updates, cas.get_logout_url(
                    cas.get_login_url(
                        service_url,
                        username=user.username,
                        verification_key=user.verification_key,
                    ),
                )

            # if user is authenticated by CAS
            print_cas_log(f'CAS response - finalizing authentication: user=[{user._id}]', LogLevel.INFO)
            session_updates = {
                'auth_user_username': user.username,
                'auth_user_id': user._primary_key,
                'auth_user_fullname': user.fullname,
                'user_reference_uri': user.get_semantic_iri(),
            }
            return user, user_updates, session_updates, None
        # first time login from external identity provider
        if not user and external_credential and action == 'external_first_login':
            print_cas_log(
                f'CAS response - first login from external IdP: '
                f'external=[{external_credential}], action=[{action}]',
                LogLevel.INFO,
            )
            # orcid attributes can be marked private and not shared, default to orcid otherwise
            fullname = f'{cas_resp.attributes.get("given-names", "")} {cas_resp.attributes.get("family-name", "")}'.strip()
            session_updates = {
                'auth_user_external_id_provider': external_credential['provider'],
                'auth_user_external_id': external_credential['id'],
                'auth_user_fullname': fullname,
                'auth_user_external_first_login': True,
                'service_url': service_furl.url,
            }
            user_identity = f'{external_credential["provider"]}#{external_credential["id"]}'
            print_cas_log(
                f'Finalizing first-time login from external IdP - data updated: user=[{user_identity}]',
                LogLevel.INFO,
            )
            print_cas_log(f'CAS response - creating anonymous session: external=[{external_credential}]', LogLevel.INFO)
            return None, None, session_updates, 'ang_route'  # TODO: ANG route for email collection page
    # Unauthorized: ticket could not be validated, or user does not exist.
    print_cas_log('Ticket validation failed or user does not exist. Redirect back to service URL (logged out).', LogLevel.ERROR)
    return None, None, None, None

@require_GET
def auth_login(request):
    ticket = request.GET.get('ticket')
    if not ticket:
        return HttpResponse('Missing ticket', status=400)

    # redirect to Angular
    next_url = request.GET.get('next', 'http://localhost:4200/')

    service_url = furl(request.build_absolute_uri()).remove(args=['ticket'])
    user, user_updates, session_updates, redirect_url = make_response_from_ticket(ticket, service_url.url)
    response = HttpResponseRedirect(redirect_url if redirect_url else next_url)

    if user:
        from django.contrib.auth import login
        login(request, user, backend='api.base.authentication.backends.ODMBackend')
        if user_updates:
            enqueue_task(update_user_from_activity.s(user._id, timezone.now().timestamp(), cas_login=True, updates=user_updates))

        from django.middleware.csrf import get_token
        csrf_token = get_token(request)
        response.set_cookie(
            api_settings.CSRF_COOKIE_NAME,
            csrf_token,
            max_age=api_settings.CSRF_COOKIE_AGE,
            domain=api_settings.CSRF_COOKIE_DOMAIN,
            path=api_settings.CSRF_COOKIE_PATH,
            httponly=api_settings.CSRF_COOKIE_HTTPONLY,
        )

    session = request.session
    for key, value in session_updates.items() if session_updates else {}:
        session[key] = value
    session.save()

    return response
