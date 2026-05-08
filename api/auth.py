from django.views.decorators.http import require_GET
from django.http import HttpResponseRedirect, HttpResponse
from website import settings
# from framework.auth.cas import CasClient
from osf.models import OSFUser


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

    user = OSFUser.objects.get(username='test@mail.com')
    login(request, user, backend='api.base.authentication.backends.ODMBackend')
    session = request.session
    data = {
        'auth_user_username': user.username,
        'auth_user_id': user._primary_key,
        'auth_user_fullname': user.fullname,
        'user_reference_uri': user.get_semantic_iri(),
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
