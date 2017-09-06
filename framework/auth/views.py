# -*- coding: utf-8 -*-
import httplib as http

import markupsafe

from django.core.exceptions import ValidationError

from flask import request

from modularodm import Q
from modularodm.exceptions import NoResultsFound
from modularodm.exceptions import ValidationValueError

from framework import sentry, status
from framework import auth as framework_auth
from framework.auth import exceptions
from framework.auth import cas, campaigns
from framework.auth import logout as osf_logout
from framework.auth.exceptions import DuplicateEmailError, ExpiredTokenError, InvalidTokenError, ChangePasswordError
from framework.auth.core import generate_verification_key
from framework.auth.decorators import block_bing_preview, collect_auth, must_be_logged_in
from framework.auth.utils import validate_recaptcha
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.sessions.utils import remove_sessions_for_user

from osf.models import OSFUser

from website import settings, mails, language
from website.util import web_url_for
from website.util.sanitize import strip_html


@collect_auth
def auth_cas_action(auth, uid):
    """
    The service view for successful CAS verification. 'action' parameter defines the type of verification, e.g. reset
    password, verify email for new account and external id. The final landing page and whether push notification is
    shown depends on the `action` and the `next` parameter.

    :param auth: the auth, user must be authenticated
    :param uid: the GUID of the user, which must match the GUID of the auth.user
    :return: redirect to the final landing page
    :raises: HTTP 400, 403
    """

    if not auth or not auth.user or auth.user._id != uid:
        raise HTTPError(http.FORBIDDEN)

    cas_action = request.args.get('action', None)
    next_url = request.args.get('next', None)

    if not cas_action:
        raise HTTPError(http.BAD_REQUEST)

    if 'account-password-reset' == cas_action:
        status.push_status_message(language.PASSWORD_RESET_SUCCESS, kind='success', trust=True)
        return redirect(web_url_for('user_account'))

    if 'account-password-meetings' == cas_action:
        status.push_status_message(language.PASSWORD_SET_SUCCESS, kind='success', trust=True)
        return redirect(web_url_for('user_profile'))

    if 'account-verify-osf' == cas_action:
        campaign = campaigns.campaign_for_user(auth.user)
        if campaign:
            return redirect(campaigns.campaign_url_for(campaign))
        status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
        return redirect(web_url_for('index'))

    if 'account-verify-external' == cas_action:
        if not next_url:
            campaign = campaigns.campaign_for_user(auth.user)
            if campaign:
                return redirect(campaigns.campaign_url_for(campaign))
            return redirect(web_url_for('index'))
        validate_next_url(next_url)
        return redirect(next_url)

    raise HTTPError(http.BAD_REQUEST)


def login_and_register_handler(auth, login=True, campaign=None, next_url=None, logout=None):
    """
    Non-view helper to handle `login` and `register` requests.

    :param auth: the auth context
    :param login: `True` if `GET /login`, `False` if `GET /register`
    :param campaign: a target campaign defined in `auth.campaigns`
    :param next_url: the service url for CAS login or redirect url for OSF
    :param logout: used only for `claim_user_registered`
    :return: data object that contains actions for `auth_register` and `auth_login`
    :raises: http.BAD_REQUEST
    """

    # Only allow redirects which are relative root or full domain. Disallows external redirects.
    if next_url and not validate_next_url(next_url):
        raise HTTPError(http.BAD_REQUEST)

    data = {
        'status_code': http.FOUND if login else http.OK,
        'next_url': next_url,
        'campaign': None,
        'must_login_warning': False,
    }

    # login or register with campaign parameter
    if campaign:
        if validate_campaign(campaign):
            # GET `/register` or '/login` with `campaign=institution`
            # unlike other campaigns, institution login serves as an alternative for authentication
            if campaign == 'institution':
                next_url = web_url_for('dashboard', _absolute=True)
                data['status_code'] = http.FOUND
                if auth.logged_in:
                    data['next_url'] = next_url
                else:
                    data['next_url'] = cas.get_login_url(next_url, campaign='institution')
            # for non-institution campaigns
            else:
                destination = next_url if next_url else campaigns.campaign_url_for(campaign)
                if auth.logged_in:
                    # if user is already logged in, go to the campaign landing page
                    data['status_code'] = http.FOUND
                    data['next_url'] = destination
                else:
                    # if user is logged out, go to the osf register page with campaign context
                    if login:
                        # `GET /login?campaign=...`
                        data['next_url'] = web_url_for('auth_register', campaign=campaign, next=destination)
                    else:
                        # `GET /register?campaign=...`
                        data['campaign'] = campaign
                        if campaigns.is_proxy_login(campaign):
                            data['next_url'] = web_url_for(
                                'auth_login',
                                next=destination,
                                _absolute=True
                            )
                        else:
                            data['next_url'] = destination
        else:
            # invalid campaign, inform sentry and redirect to non-campaign sign up or sign in
            redirect_view = 'auth_login' if login else 'auth_register'
            data['status_code'] = http.FOUND
            data['next_url'] = web_url_for(redirect_view, campaigns=None, next=next_url)
            data['campaign'] = None
            sentry.log_message(
                '{} is not a valid campaign. Please add it if this is a new one'.format(campaign)
            )
    # login or register with next parameter
    elif next_url:
        if logout:
            # handle `claim_user_registered`
            data['next_url'] = next_url
            if auth.logged_in:
                # log user out and come back
                data['status_code'] = 'auth_logout'
            else:
                # after logout, land on the register page with "must_login" warning
                data['status_code'] = http.OK
                data['must_login_warning'] = True
        elif auth.logged_in:
            # if user is already logged in, redirect to `next_url`
            data['status_code'] = http.FOUND
            data['next_url'] = next_url
        elif login:
            # `/login?next=next_url`: go to CAS login page with current request url as service url
            data['status_code'] = http.FOUND
            data['next_url'] = cas.get_login_url(request.url)
        else:
            # `/register?next=next_url`: land on OSF register page with request url as next url
            data['status_code'] = http.OK
            data['next_url'] = request.url
    else:
        # `/login/` or `/register/` without any parameter
        if auth.logged_in:
            data['status_code'] = http.FOUND
        data['next_url'] = web_url_for('dashboard', _absolute=True)

    return data


@collect_auth
def auth_login(auth):
    """
    View (no template) for OSF Login.
    Redirect user based on `data` returned from `login_and_register_handler`.

    `/login` only takes valid campaign, valid next, or no query parameter
    `login_and_register_handler()` handles the following cases:
        if campaign and logged in, go to campaign landing page (or valid next_url if presents)
        if campaign and logged out, go to campaign register page (with next_url if presents)
        if next_url and logged in, go to next url
        if next_url and logged out, go to cas login page with current request url as service parameter
        if none, go to `/dashboard` which is decorated by `@must_be_logged_in`

    :param auth: the auth context
    :return: redirects
    """

    campaign = request.args.get('campaign')
    next_url = request.args.get('next')

    data = login_and_register_handler(auth, login=True, campaign=campaign, next_url=next_url)
    if data['status_code'] == http.FOUND:
        return redirect(data['next_url'])


@collect_auth
def auth_register(auth):
    """
    View for OSF register. Final destination depends on the `data` object returned by login_and_register_handler().
    "/register/" only takes a valid campaign, a valid next url, the logout flag or no query parameter. Please refer to
     login_and_register_handler() for further information.

    1. Redirect to CAS register page with data['next_url'] as service, if data[status_code] is http.OK
        1.1 When we moved the register page form OSF to CAS, anything of which the final destination was the register
        page should be redirected to the new CAS register page. The campaign and final destination information is
        carried over with the data[`next_url`] which can be identified by CAS through registered service matching.
        data[`campaign`] became deprecated.
    2. Redirect to data['next_url'], if data['status_code'] is http.Found
    3. Redirect to auth_logout() with data['next_url'] as redirect url, if data['status_code'] is 'auth_logout'

    :param auth: the auth context
    :return: redirect
    :raise: http.BAD_REQUEST
    """

    # a target campaign in `auth.campaigns`
    campaign = request.args.get('campaign')
    # the service url for CAS login or redirect url for OSF
    next_url = request.args.get('next')
    # used only for `claim_user_registered`
    logout = request.args.get('logout')

    # logout must have next_url
    if logout and not next_url:
        raise HTTPError(http.BAD_REQUEST)

    data = login_and_register_handler(auth, login=False, campaign=campaign, next_url=next_url, logout=logout)

    # land on register page
    if data['status_code'] == http.OK:
        # TODO: should we port this warning to CAS?
        # if data['must_login_warning']:
        #     status.push_status_message(language.MUST_LOGIN, trust=False)
        return redirect(cas.get_account_register_url(data['next_url']))
    # redirect to url
    elif data['status_code'] == http.FOUND:
        return redirect(data['next_url'])
    # go to other views
    elif data['status_code'] == 'auth_logout':
        return auth_logout(redirect_url=data['next_url'])

    raise HTTPError(http.BAD_REQUEST)


@collect_auth
def auth_logout(auth, redirect_url=None, next_url=None):
    """
    Log out, delete current session and remove OSF cookie.
    If next url is valid and auth is logged in, redirect to CAS logout endpoint with the current request url as service.
    If next url is valid and auth is logged out, redirect directly to the next url.
    Otherwise, redirect to CAS logout or login endpoint with redirect url as service.
    The CAS logout endpoint which clears sessions and cookies for CAS and Shibboleth.
    HTTP Method: GET

    Note 1: OSF tells CAS where it wants to be redirected back after successful logout. However, CAS logout flow may not
    respect this url if user is authenticated through remote identity provider.
    Note 2: The name of the query parameter is `next`, `next_url` is used to avoid python reserved word.

    :param auth: the authentication context
    :param redirect_url: url to DIRECTLY redirect after CAS logout, default is `OSF/goodbye`
    :param next_url: url to redirect after OSF logout, which is after CAS logout
    :return: the response
    """

    # For `?next=`:
    #   takes priority
    #   the url must be a valid OSF next url,
    #   the full request url is set to CAS service url,
    #   does not support `reauth`
    # For `?redirect_url=`:
    #   the url must be valid CAS service url
    #   the redirect url is set to CAS service url.
    #   support `reauth`

    # logout/?next=<an OSF verified next url>
    next_url = next_url or request.args.get('next', None)
    if next_url and validate_next_url(next_url):
        cas_logout_endpoint = cas.get_logout_url(request.url)
        if auth.logged_in:
            resp = redirect(cas_logout_endpoint)
        else:
            resp = redirect(next_url)
    # logout/ or logout/?redirect_url=<a CAS verified redirect url>
    else:
        redirect_url = redirect_url or request.args.get('redirect_url') or web_url_for('goodbye', _absolute=True)
        # set redirection to CAS log out (or log in if `reauth` is present)
        if 'reauth' in request.args:
            cas_endpoint = cas.get_login_url(redirect_url)
        else:
            cas_endpoint = cas.get_logout_url(redirect_url)
        resp = redirect(cas_endpoint)

    # perform OSF logout
    osf_logout()

    # set response to delete OSF cookie
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)

    return resp


def auth_email_logout(token, user):
    """
    When a user is adding an email or merging an account, add the email to the user and log them out.
    """

    redirect_url = cas.get_logout_url(service_url=cas.get_login_url(service_url=web_url_for('index', _absolute=True)))
    try:
        unconfirmed_email = user.get_unconfirmed_email_for_token(token)
    except InvalidTokenError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Bad token',
            'message_long': 'The provided token is invalid.'
        })
    except ExpiredTokenError:
        status.push_status_message('The private link you used is expired.')
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Expired link',
            'message_long': 'The private link you used is expired.'
        })
    try:
        user_merge = OSFUser.find_one(Q('emails__address', 'eq', unconfirmed_email))
    except NoResultsFound:
        user_merge = False
    if user_merge:
        remove_sessions_for_user(user_merge)
    user.email_verifications[token]['confirmed'] = True
    user.save()
    remove_sessions_for_user(user)
    resp = redirect(redirect_url)
    resp.delete_cookie(settings.COOKIE_NAME, domain=settings.OSF_COOKIE_DOMAIN)
    return resp


@block_bing_preview
@collect_auth
def confirm_email_get(token, auth=None, **kwargs):
    """
    View for email confirmation links. Authenticates and redirects to user settings page if confirmation is successful,
    otherwise shows an "Expired Link" error.
    HTTP Method: GET
    """

    user = OSFUser.load(kwargs['uid'])
    is_merge = 'confirm_merge' in request.args
    is_initial_confirmation = not user.date_confirmed
    log_out = request.args.get('logout', None)

    if user is None:
        raise HTTPError(http.NOT_FOUND)

    # if the user is merging or adding an email (they already are an osf user)
    if log_out:
        return auth_email_logout(token, user)

    if auth and auth.user and (auth.user._id == user._id or auth.user._id == user.merged_by._id):
        if not is_merge:
            # determine if the user registered through a campaign
            campaign = campaigns.campaign_for_user(user)
            if campaign:
                return redirect(campaigns.campaign_url_for(campaign))

            # go to home page with push notification
            if auth.user.emails.count() == 1 and len(auth.user.email_verifications) == 0:
                status.push_status_message(language.WELCOME_MESSAGE, kind='default', jumbotron=True, trust=True)
            if token in auth.user.email_verifications:
                status.push_status_message(language.CONFIRM_ALTERNATE_EMAIL_ERROR, kind='danger', trust=True)
            return redirect(web_url_for('index'))

        status.push_status_message(language.MERGE_COMPLETE, kind='success', trust=False)
        return redirect(web_url_for('user_account'))

    try:
        user.confirm_email(token, merge=is_merge)
    except exceptions.EmailConfirmTokenError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })

    if is_initial_confirmation:
        user.update_date_last_login()
        user.save()

        # send out our welcome message
        mails.send_mail(
            to_addr=user.username,
            mail=mails.WELCOME,
            mimetype='html',
            user=user
        )

    # new random verification key, allows CAS to authenticate the user w/o password one-time only.
    user.verification_key = generate_verification_key()
    user.save()
    # redirect to CAS and authenticate the user with a verification key.
    return redirect(cas.get_login_url(
        request.url,
        username=user.username,
        verification_key=user.verification_key
    ))


@must_be_logged_in
def unconfirmed_email_remove(auth=None):
    """
    Called at login if user cancels their merge or email add.
    HTTP Method: DELETE
    """

    user = auth.user
    json_body = request.get_json()
    try:
        given_token = json_body['token']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Missing token',
            'message_long': 'Must provide a token'
        })
    user.clean_email_verifications(given_token=given_token)
    user.save()
    return {
        'status': 'success',
        'removed_email': json_body['address']
    }, 200


@must_be_logged_in
def unconfirmed_email_add(auth=None):
    """
    Called at login if user confirms their merge or email add.
    HTTP Method: PUT
    """
    user = auth.user
    json_body = request.get_json()
    try:
        token = json_body['token']
    except KeyError:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': 'Missing token',
            'message_long': 'Must provide a token'
        })
    try:
        user.confirm_email(token, merge=True)
    except exceptions.InvalidTokenError:
        raise InvalidTokenError(http.BAD_REQUEST, data={
            'message_short': 'Invalid user token',
            'message_long': 'The user token is invalid'
        })
    except exceptions.EmailConfirmTokenError as e:
        raise HTTPError(http.BAD_REQUEST, data={
            'message_short': e.message_short,
            'message_long': e.message_long
        })

    user.save()
    return {
        'status': 'success',
        'removed_email': json_body['address']
    }, 200


def send_confirm_email(user, email, renew=False, external_id_provider=None, external_id=None, destination=None):
    """
    Sends `user` a confirmation to the given `email`.


    :param user: the user
    :param email: the email
    :param renew: refresh the token
    :param external_id_provider: user's external id provider
    :param external_id: user's external id
    :param destination: the destination page to redirect after confirmation
    :return:
    :raises: KeyError if user does not have a confirmation token for the given email.
    """

    # legacy design: user click the confirmation url, where HTTP GET request is used to change server state
    confirmation_url = user.get_confirmation_url(
        email,
        external=True,
        force=True,
        renew=renew,
        external_id_provider=external_id_provider,
        destination=destination
    )

    # best-of-practice design: ask user to submit the verification code
    verification_code = user.get_confirmation_token(email, force=True, renew=renew)
    cas_confirmation_url = cas.get_confirmation_url(user._id)

    try:
        merge_target = OSFUser.find_one(Q('emails__address', 'eq', email))
    except NoResultsFound:
        merge_target = None

    campaign = campaigns.campaign_for_user(user)
    branded_preprints_provider = None

    # Choose the appropriate email template to use and add existing_user flag if a merge or adding an email.
    if external_id_provider and external_id:
        # First time login through external identity provider, link or create an OSF account confirmation
        if user.external_identity[external_id_provider][external_id] == 'CREATE':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_CREATE
        elif user.external_identity[external_id_provider][external_id] == 'LINK':
            mail_template = mails.EXTERNAL_LOGIN_CONFIRM_EMAIL_LINK
    elif merge_target:
        # Merge account confirmation
        mail_template = mails.CONFIRM_MERGE
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif user.is_active:
        # Add email confirmation
        mail_template = mails.CONFIRM_EMAIL
        confirmation_url = '{}?logout=1'.format(confirmation_url)
    elif campaign:
        # Account creation confirmation: from campaign
        mail_template = campaigns.email_template_for_campaign(campaign)
        if campaigns.is_proxy_login(campaign) and campaigns.get_service_provider(campaign) != 'OSF':
            branded_preprints_provider = campaigns.get_service_provider(campaign)
    else:
        # Account creation confirmation: from OSF
        mail_template = mails.INITIAL_CONFIRM_EMAIL

    mails.send_mail(
        email,
        mail_template,
        'plain',
        user=user,
        confirmation_url=confirmation_url,
        verification_code=verification_code,
        cas_confirmation_url=cas_confirmation_url,
        email=email,
        merge_target=merge_target,
        external_id_provider=external_id_provider,
        branded_preprints_provider=branded_preprints_provider
    )


def register_user(**kwargs):
    """
    Register a new unconfirmed user.
    Note: this is a V1 API, only used for user sign up on the OSF home page.

    HTTP Method: POST

    :param-json str email1:
    :param-json str email2:
    :param-json str password:
    :param-json str fullName:
    :param-json str campaign:
    :raises: HTTPError(http.BAD_REQUEST) if validation fails or user already exists
    """

    json_data = request.get_json()

    # Verify that captcha is valid
    if settings.RECAPTCHA_SITE_KEY and not validate_recaptcha(json_data.get('g-recaptcha-response'), remote_ip=request.remote_addr):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Invalid Captcha')
        )

    fullname = json_data.get('fullName', None)
    email1 = json_data.get('email1', None)
    email2 = json_data.get('email2', None)
    password = json_data.get('password', None)
    campaign = json_data.get('campaign', None)

    # check all required information is provided
    if not (fullname and email1 and email2 and password):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Missing credentials')
        )

    # verify that emails match
    if str(email1).lower().strip() != str(email2).lower().strip():
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long='Email addresses must match')
        )

    # sanitize fullname
    fullname = strip_html(fullname)

    try:
        user = framework_auth.register_unconfirmed(email1, password, fullname, campaign=campaign)
    except (ValidationValueError, DuplicateEmailError):
        raise HTTPError(
            http.BAD_REQUEST,
            data=dict(message_long=language.ALREADY_REGISTERED.format(email=markupsafe.escape(request.json['email1'])))
        )
    except ValidationError as e:
        raise HTTPError(http.BAD_REQUEST, data=dict(message_long=e.message))
    except ChangePasswordError as e:
        raise HTTPError(http.BAD_REQUEST, data=dict(message_long='Password cannot be the same as your email'))

    # TODO: is this correct? `register_unconfirmed()` already sends a signal of the creation of an unconfirmed user
    framework_auth.signals.user_registered.send(user)
    try:
        send_confirm_email(user, email=user.username, renew=False, external_id_provider=None, external_id=None)
    except KeyError:
        raise HTTPError(http.INTERNAL_SERVER_ERROR, data=dict(message_long='Request failed. Please try again later.'))

    return {'message': language.REGISTRATION_SUCCESS.format(email=user.username)}


def validate_campaign(campaign):
    """
    Non-view helper function that validates `campaign`.

    :param campaign: the campaign to validate
    :return: True if valid, False otherwise
    """

    return campaign and campaign in campaigns.get_campaigns()


def validate_next_url(next_url):
    """
    Non-view helper function that checks `next_url`.
    Only allow redirects which are relative root or full domain (CAS, OSF and MFR).
    Disallows external redirects.

    :param next_url: the next url to check
    :return: True if valid, False otherwise
    """

    # disable external domain using `//`: the browser allows `//` as a shortcut for non-protocol specific requests
    # like http:// or https:// depending on the use of SSL on the page already.
    if next_url.startswith('//'):
        return False

    # only OSF, MFR, CAS and Branded Preprints domains are allowed
    if next_url[0] == '/' or next_url.startswith(settings.DOMAIN):
        # OSF
        return True
    if next_url.startswith(settings.CAS_SERVER_URL) or next_url.startswith(settings.MFR_SERVER_URL):
        # CAS or MFR
        return True
    for url in campaigns.get_external_domains():
        # Branded Preprints Phase 2
        if next_url.startswith(url):
            return True

    return False


def check_service_url_with_proxy_campaign(service_url, campaign_url, external_campaign_url=None):
    """
    Check if service url belongs to proxy campaigns: OSF Preprints and branded ones.
    Both service_url and campaign_url are parsed using `furl` encoding scheme.

    :param service_url: the `furl` formatted service url
    :param campaign_url: the `furl` formatted campaign url
    :param external_campaign_url: the `furl` formatted external campaign url
    :return: the matched object or None
    """

    prefix_1 = settings.DOMAIN + 'login/?next=' + campaign_url
    prefix_2 = settings.DOMAIN + 'login?next=' + campaign_url

    valid = service_url.startswith(prefix_1) or service_url.startswith(prefix_2)
    valid_external = False

    if external_campaign_url:
        prefix_3 = settings.DOMAIN + 'login/?next=' + external_campaign_url
        prefix_4 = settings.DOMAIN + 'login?next=' + external_campaign_url
        valid_external = service_url.startswith(prefix_3) or service_url.startswith(prefix_4)

    return valid or valid_external
