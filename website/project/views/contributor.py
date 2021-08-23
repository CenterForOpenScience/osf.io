# -*- coding: utf-8 -*-

from rest_framework import status as http_status

from flask import request
from django.core.exceptions import ValidationError
from django.utils import timezone

from framework import forms, status
from framework.auth import cas
from framework.auth.core import get_user, generate_verification_key
from framework.auth.decorators import block_bing_preview, collect_auth, must_be_logged_in
from framework.auth.forms import PasswordForm, SetEmailAndPasswordForm
from framework.auth.signals import user_registered
from framework.auth.utils import validate_email, validate_recaptcha
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.sessions import session
from framework.transactions.handlers import no_auto_transaction
from framework.utils import get_timestamp, throttle_period_expired
from osf.models import Tag
from osf.exceptions import NodeStateError
from osf.models import AbstractNode, DraftRegistration, OSFGroup, OSFUser, Preprint, PreprintProvider, RecentlyAddedContributor
from osf.utils import sanitize
from osf.utils.permissions import ADMIN
from website import mails, language, settings
from website.notifications.utils import check_if_all_global_subscriptions_are_none
from website.profile import utils as profile_utils
from website.project.decorators import (must_have_permission, must_be_valid_project, must_not_be_registration,
                                        must_be_contributor_or_public, must_be_contributor)
from website.project.views.node import serialize_preprints
from website.project.model import has_anonymous_link
from website.project.signals import unreg_contributor_added, contributor_added
from website.util import web_url_for, is_json_request
from website.util.metrics import provider_claimed_tag
from framework.auth.campaigns import NODE_SOURCE_TAG_CLAIMED_TAG_RELATION


@collect_auth
@must_be_valid_project(retractions_valid=True)
def get_node_contributors_abbrev(auth, node, **kwargs):
    anonymous = has_anonymous_link(node, auth)
    formatter = 'surname'
    max_count = kwargs.get('max_count', 3)
    if 'user_ids' in kwargs:
        users = [
            OSFUser.load(user_id) for user_id in kwargs['user_ids']
            if node.contributor_set.filter(user__guid__guid=user_id).exists()
        ]
    else:
        users = node.visible_contributors

    if anonymous or not node.can_view(auth):
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    contributors = []

    n_contributors = len(users)
    others_count = ''

    for index, user in enumerate(users[:max_count]):

        if index == max_count - 1 and len(users) > max_count:
            separator = ' &'
            others_count = str(n_contributors - 3)
        elif index == len(users) - 1:
            separator = ''
        elif index == len(users) - 2:
            separator = ' &'
        else:
            separator = ','
        contributor = user.get_summary(formatter)
        contributor['user_id'] = user._primary_key
        contributor['separator'] = separator

        contributors.append(contributor)

    return {
        'contributors': contributors,
        'others_count': others_count,
    }


@collect_auth
@must_be_valid_project(retractions_valid=True)
def get_contributors(auth, node, **kwargs):

    # Can set limit to only receive a specified number of contributors in a call to this route
    if request.args.get('limit'):
        try:
            limit = int(request.args['limit'])
        except ValueError:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
                message_long='Invalid value for "limit": {}'.format(request.args['limit'])
            ))
    else:
        limit = None

    anonymous = has_anonymous_link(node, auth)

    if anonymous or not node.can_view(auth):
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    # Limit is either an int or None:
    # if int, contribs list is sliced to specified length
    # if None, contribs list is not sliced
    contribs = profile_utils.serialize_contributors(
        node.visible_contributors[0:limit],
        node=node,
    )

    # Will either return just contributor list or contributor list + 'more' element
    if limit:
        return {
            'contributors': contribs,
            'more': max(0, len(node.visible_contributors) - limit)
        }
    else:
        return {'contributors': contribs}


@must_be_logged_in
@must_be_valid_project
def get_contributors_from_parent(auth, node, **kwargs):

    parent = node.parent_node

    if not parent:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    if not node.can_view(auth):
        raise HTTPError(http_status.HTTP_403_FORBIDDEN)

    contribs = [
        profile_utils.add_contributor_json(contrib, node=node)
        for contrib in parent.contributors if contrib not in node.contributors
    ]

    return {'contributors': contribs}


def deserialize_contributors(node, user_dicts, auth, validate=False):
    """View helper that returns a list of User objects from a list of
    serialized users (dicts). The users in the list may be registered or
    unregistered users.

    e.g. ``[{'id': 'abc123', 'registered': True, 'fullname': ..},
            {'id': None, 'registered': False, 'fullname'...},
            {'id': '123ab', 'registered': False, 'fullname': ...}]

    If a dict represents an unregistered user without an ID, creates a new
    unregistered User record.

    :param Node node: The node to add contributors to
    :param list(dict) user_dicts: List of serialized users in the format above.
    :param Auth auth:
    :param bool validate: Whether to validate and sanitize fields (if necessary)
    """

    # Add the registered contributors
    contribs = []
    for contrib_dict in user_dicts:
        fullname = contrib_dict['fullname']
        visible = contrib_dict['visible']
        email = contrib_dict.get('email')

        if validate is True:
            # Validate and sanitize inputs as needed. Email will raise error if invalid.
            # TODO Edge case bug: validation and saving are performed in same loop, so all in list
            # up to the invalid entry will be saved. (communicate to the user what needs to be retried)
            fullname = sanitize.strip_html(fullname)
            if not fullname:
                raise ValidationError('Full name field cannot be empty')
            if email:
                validate_email(email)  # Will raise a ValidationError if email invalid

        if contrib_dict['id']:
            contributor = OSFUser.load(contrib_dict['id'])
        else:
            try:
                contributor = OSFUser.create_unregistered(
                    fullname=fullname,
                    email=email)
                contributor.save()
            except ValidationError:
                ## FIXME: This suppresses an exception if ID not found & new validation fails; get_user will return None
                contributor = get_user(email=email)

        # Add unclaimed record if necessary
        if not contributor.is_registered:
            contributor.add_unclaimed_record(node, referrer=auth.user,
                given_name=fullname,
                email=email)
            contributor.save()

        contribs.append({
            'user': contributor,
            'visible': visible,
            'permissions': contrib_dict.get('permission')
        })
    return contribs


@unreg_contributor_added.connect
def finalize_invitation(node, contributor, auth, email_template='default'):
    try:
        record = contributor.get_unclaimed_record(node._primary_key)
    except ValueError:
        pass
    else:
        if record['email']:
            send_claim_email(record['email'], contributor, node, notify=True, email_template=email_template)


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def project_contributors_post(auth, node, **kwargs):
    """ Add contributors to a node. """
    user_dicts = request.json.get('users')
    node_ids = request.json.get('node_ids')
    if node._id in node_ids:
        node_ids.remove(node._id)

    if user_dicts is None or node_ids is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    # Prepare input data for `Node::add_contributors`
    try:
        contribs = deserialize_contributors(node, user_dicts, auth=auth, validate=True)
    except ValidationError as e:
        return {'status': 400, 'message': e.message}, 400

    try:
        node.add_contributors(contributors=contribs, auth=auth)
    except NodeStateError as e:
        return {'status': 400, 'message': e.args[0]}, 400

    node.save()

    # Disconnect listener to avoid multiple invite emails
    unreg_contributor_added.disconnect(finalize_invitation)

    for child_id in node_ids:
        child = AbstractNode.load(child_id)
        # Only email unreg users once
        try:
            child_contribs = deserialize_contributors(
                child, user_dicts, auth=auth, validate=True
            )
        except ValidationError as e:
            return {'status': 400, 'message': e.message}, 400

        child.add_contributors(contributors=child_contribs, auth=auth)
        child.save()
    # Reconnect listeners
    unreg_contributor_added.connect(finalize_invitation)

    return {
        'status': 'success',
        'contributors': profile_utils.serialize_contributors(
            node.visible_contributors,
            node=node,
        )
    }, 201


@no_auto_transaction
@must_be_valid_project  # injects project
@must_have_permission(ADMIN)
@must_not_be_registration
def project_manage_contributors(auth, node, **kwargs):
    """Reorder and remove contributors.

    :param Auth auth: Consolidated authorization
    :param-json list contributors: Ordered list of contributors represented as
        dictionaries of the form:
        {'id': <id>, 'permission': <One of 'read', 'write', 'admin'>}
    :raises: HTTPError(400) if contributors to be removed are not in list
        or if no admin users would remain after changes were applied

    """
    contributors = request.json.get('contributors')

    # Update permissions and order
    try:
        node.manage_contributors(contributors, auth=auth, save=True)
    except (ValueError, NodeStateError) as error:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={'message_long': error.args[0]})

    # If user has removed herself from project, alert; redirect to
    # node summary if node is public, else to user's dashboard page
    if not node.is_contributor_or_group_member(auth.user):
        status.push_status_message(
            'You have removed yourself as a contributor from this project',
            kind='success',
            trust=False
        )
        if node.is_public:
            return {'redirectUrl': node.url}
        return {'redirectUrl': web_url_for('dashboard')}
    # Else if user has revoked her admin permissions, alert and stay on
    # current page
    if not node.has_permission(auth.user, ADMIN):
        status.push_status_message(
            'You have removed your administrative privileges for this project',
            kind='success',
            trust=False
        )
    # Else stay on current page
    return {}


@must_be_valid_project  # returns project
@must_be_contributor
@must_not_be_registration
def project_remove_contributor(auth, **kwargs):
    """Remove a contributor from a list of nodes.

    :param Auth auth: Consolidated authorization
    :raises: HTTPError(400) if contributors to be removed are not in list
        or if no admin users would remain after changes were applied

    """
    contributor_id = request.get_json()['contributorID']
    node_ids = request.get_json()['nodeIDs']
    contributor = OSFUser.load(contributor_id)
    if contributor is None:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={'message_long': 'Contributor not found.'})
    redirect_url = {}
    parent_id = node_ids[0]
    for node_id in node_ids:
        # Update permissions and order
        node = AbstractNode.load(node_id)

        # Forbidden unless user is removing herself
        if not node.has_permission(auth.user, ADMIN):
            if auth.user != contributor:
                raise HTTPError(http_status.HTTP_403_FORBIDDEN)

        if node.visible_contributors.count() == 1 \
                and node.visible_contributors[0] == contributor:
            raise HTTPError(http_status.HTTP_403_FORBIDDEN, data={
                'message_long': 'Must have at least one bibliographic contributor'
            })

        nodes_removed = node.remove_contributor(contributor, auth=auth)
        # remove_contributor returns false if there is not one admin or visible contributor left after the move.
        if not nodes_removed:
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data={
                'message_long': 'Could not remove contributor.'})

        # On parent node, if user has removed herself from project, alert; redirect to
        # node summary if node is public, else to user's dashboard page
        if not node.is_contributor_or_group_member(auth.user) and node_id == parent_id:
            status.push_status_message(
                'You have removed yourself as a contributor from this project',
                kind='success',
                trust=False,
                id='remove_self_contrib'
            )
            if node.is_public:
                redirect_url = {'redirectUrl': node.url}
            else:
                redirect_url = {'redirectUrl': web_url_for('dashboard')}
    return redirect_url


# TODO: consider moving this into utils
def send_claim_registered_email(claimer, unclaimed_user, node, throttle=24 * 3600):
    """
    A registered user claiming the unclaimed user account as an contributor to a project.
    Send an email for claiming the account to the referrer and notify the claimer.

    :param claimer: the claimer
    :param unclaimed_user: the user account to claim
    :param node: the project node where the user account is claimed
    :param throttle: the time period in seconds before another claim for the account can be made
    :return:
    :raise: http_status.HTTP_400_BAD_REQUEST
    """

    unclaimed_record = unclaimed_user.get_unclaimed_record(node._primary_key)

    # check throttle
    timestamp = unclaimed_record.get('last_sent')
    if not throttle_period_expired(timestamp, throttle):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
            message_long='User account can only be claimed with an existing user once every 24 hours'
        ))

    # roll the valid token for each email, thus user cannot change email and approve a different email address
    verification_key = generate_verification_key(verification_type='claim')
    unclaimed_record['token'] = verification_key['token']
    unclaimed_record['expires'] = verification_key['expires']
    unclaimed_record['claimer_email'] = claimer.username
    unclaimed_user.save()

    referrer = OSFUser.load(unclaimed_record['referrer_id'])
    claim_url = web_url_for(
        'claim_user_registered',
        uid=unclaimed_user._primary_key,
        pid=node._primary_key,
        token=unclaimed_record['token'],
        _absolute=True,
    )

    # Send mail to referrer, telling them to forward verification link to claimer
    mails.send_mail(
        referrer.username,
        mails.FORWARD_INVITE_REGISTERED,
        user=unclaimed_user,
        referrer=referrer,
        node=node,
        claim_url=claim_url,
        fullname=unclaimed_record['name'],
        can_change_preferences=False,
        osf_contact_email=settings.OSF_CONTACT_EMAIL,
    )
    unclaimed_record['last_sent'] = get_timestamp()
    unclaimed_user.save()

    # Send mail to claimer, telling them to wait for referrer
    mails.send_mail(
        claimer.username,
        mails.PENDING_VERIFICATION_REGISTERED,
        fullname=claimer.fullname,
        referrer=referrer,
        node=node,
        can_change_preferences=False,
        osf_contact_email=settings.OSF_CONTACT_EMAIL,
    )


# TODO: consider moving this into utils
def send_claim_email(email, unclaimed_user, node, notify=True, throttle=24 * 3600, email_template='default'):
    """
    Unregistered user claiming a user account as an contributor to a project. Send an email for claiming the account.
    Either sends to the given email or the referrer's email, depending on the email address provided.

    :param str email: The address given in the claim user form
    :param User unclaimed_user: The User record to claim.
    :param Node node: The node where the user claimed their account.
    :param bool notify: If True and an email is sent to the referrer, an email
        will also be sent to the invited user about their pending verification.
    :param int throttle: Time period (in seconds) after the referrer is
        emailed during which the referrer will not be emailed again.
    :param str email_template: the email template to use
    :return
    :raise http_status.HTTP_400_BAD_REQUEST

    """

    claimer_email = email.lower().strip()
    unclaimed_record = unclaimed_user.get_unclaimed_record(node._primary_key)
    referrer = OSFUser.load(unclaimed_record['referrer_id'])
    claim_url = unclaimed_user.get_claim_url(node._primary_key, external=True)

    # Option 1:
    #   When adding the contributor, the referrer provides both name and email.
    #   The given email is the same provided by user, just send to that email.
    logo = None
    if unclaimed_record.get('email') == claimer_email:
        # check email template for branded preprints
        if email_template == 'preprint':
            if node.provider.is_default:
                mail_tpl = mails.INVITE_OSF_PREPRINT
                logo = settings.OSF_PREPRINTS_LOGO
            else:
                mail_tpl = mails.INVITE_PREPRINT(node.provider)
                logo = node.provider._id
        elif email_template == 'draft_registration':
            mail_tpl = mails.INVITE_DRAFT_REGISTRATION
        else:
            mail_tpl = mails.INVITE_DEFAULT

        to_addr = claimer_email
        unclaimed_record['claimer_email'] = claimer_email
        unclaimed_user.save()
    # Option 2:
    # TODO: [new improvement ticket] this option is disabled from preprint but still available on the project page
    #   When adding the contributor, the referred only provides the name.
    #   The account is later claimed by some one who provides the email.
    #   Send email to the referrer and ask her/him to forward the email to the user.
    else:
        # check throttle
        timestamp = unclaimed_record.get('last_sent')
        if not throttle_period_expired(timestamp, throttle):
            raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
                message_long='User account can only be claimed with an existing user once every 24 hours'
            ))
        # roll the valid token for each email, thus user cannot change email and approve a different email address
        verification_key = generate_verification_key(verification_type='claim')
        unclaimed_record['last_sent'] = get_timestamp()
        unclaimed_record['token'] = verification_key['token']
        unclaimed_record['expires'] = verification_key['expires']
        unclaimed_record['claimer_email'] = claimer_email
        unclaimed_user.save()

        claim_url = unclaimed_user.get_claim_url(node._primary_key, external=True)
        # send an email to the invited user without `claim_url`
        if notify:
            pending_mail = mails.PENDING_VERIFICATION
            mails.send_mail(
                claimer_email,
                pending_mail,
                user=unclaimed_user,
                referrer=referrer,
                fullname=unclaimed_record['name'],
                node=node,
                can_change_preferences=False,
                osf_contact_email=settings.OSF_CONTACT_EMAIL,
            )
        mail_tpl = mails.FORWARD_INVITE
        to_addr = referrer.username

    # Send an email to the claimer (Option 1) or to the referrer (Option 2) with `claim_url`
    mails.send_mail(
        to_addr,
        mail_tpl,
        user=unclaimed_user,
        referrer=referrer,
        node=node,
        claim_url=claim_url,
        email=claimer_email,
        fullname=unclaimed_record['name'],
        branded_service=node.provider,
        can_change_preferences=False,
        logo=logo if logo else settings.OSF_LOGO,
        osf_contact_email=settings.OSF_CONTACT_EMAIL,
    )

    return to_addr


def check_email_throttle(node, contributor, throttle=None):
    throttle = throttle or settings.CONTRIBUTOR_ADDED_EMAIL_THROTTLE
    contributor_record = contributor.contributor_added_email_records.get(node._id, {})
    if contributor_record:
        timestamp = contributor_record.get('last_sent', None)
        if timestamp:
            if not throttle_period_expired(timestamp, throttle):
                return True
    else:
        contributor.contributor_added_email_records[node._id] = {}


@contributor_added.connect
def notify_added_contributor(node, contributor, auth=None, email_template='default', throttle=None, *args, **kwargs):
    logo = settings.OSF_LOGO
    if check_email_throttle(node, contributor, throttle=throttle):
        return
    if email_template == 'false':
        return
    if not getattr(node, 'is_published', True):
        return
    if not contributor.is_registered:
        unreg_contributor_added.send(
            node,
            contributor=contributor,
            auth=auth,
            email_template=email_template
        )
        return

    # Email users for projects, or for components where they are not contributors on the parent node.
    contrib_on_parent_node = isinstance(node, (Preprint, DraftRegistration)) or \
                             (not node.parent_node or (node.parent_node and not node.parent_node.is_contributor(contributor)))
    if contrib_on_parent_node:
        if email_template == 'preprint':
            if node.provider.is_default:
                email_template = mails.CONTRIBUTOR_ADDED_OSF_PREPRINT
                logo = settings.OSF_PREPRINTS_LOGO
            else:
                email_template = mails.CONTRIBUTOR_ADDED_PREPRINT(node.provider)
                logo = node.provider._id
        elif email_template == 'draft_registration':
            email_template = mails.CONTRIBUTOR_ADDED_DRAFT_REGISTRATION
        elif email_template == 'access_request':
            email_template = mails.CONTRIBUTOR_ADDED_ACCESS_REQUEST
        elif node.has_linked_published_preprints:
            # Project holds supplemental materials for a published preprint
            email_template = mails.CONTRIBUTOR_ADDED_PREPRINT_NODE_FROM_OSF
            logo = settings.OSF_PREPRINTS_LOGO
        else:
            email_template = mails.CONTRIBUTOR_ADDED_DEFAULT

        mails.send_mail(
            to_addr=contributor.username,
            mail=email_template,
            user=contributor,
            node=node,
            referrer_name=auth.user.fullname if auth else '',
            is_initiator=getattr(auth, 'user', False) == contributor,
            all_global_subscriptions_none=check_if_all_global_subscriptions_are_none(contributor),
            branded_service=node.provider,
            can_change_preferences=False,
            logo=logo,
            osf_contact_email=settings.OSF_CONTACT_EMAIL,
            published_preprints=[] if isinstance(node, (Preprint, DraftRegistration)) else serialize_preprints(node, user=None)
        )

        contributor.contributor_added_email_records[node._id]['last_sent'] = get_timestamp()
        contributor.save()


@contributor_added.connect
def add_recently_added_contributor(node, contributor, auth=None, *args, **kwargs):
    if isinstance(node, (Preprint, DraftRegistration)):
        return
    MAX_RECENT_LENGTH = 15
    # Add contributor to recently added list for user
    if auth is not None:
        user = auth.user
        recently_added_contributor_obj, created = RecentlyAddedContributor.objects.get_or_create(
            user=user,
            contributor=contributor
        )
        recently_added_contributor_obj.date_added = timezone.now()
        recently_added_contributor_obj.save()
        count = user.recently_added.count()
        if count > MAX_RECENT_LENGTH:
            difference = count - MAX_RECENT_LENGTH
            for each in user.recentlyaddedcontributor_set.order_by('date_added')[:difference]:
                each.delete()

    # If there are pending access requests for this user, mark them as accepted
    pending_access_requests_for_user = node.requests.filter(creator=contributor, machine_state='pending')
    if pending_access_requests_for_user.exists():
        permissions = kwargs.get('permissions') or node.DEFAULT_CONTRIBUTOR_PERMISSIONS
        pending_access_requests_for_user.get().run_accept(contributor, comment='', permissions=permissions)


def verify_claim_token(user, token, pid):
    """View helper that checks that a claim token for a given user and node ID
    is valid. If not valid, throws an error with custom error messages.
    """
    # if token is invalid, throw an error
    if not user.verify_claim_token(token=token, project_id=pid):
        if user.is_registered:
            error_data = {
                'message_short': 'User has already been claimed.',
                'message_long': 'Please <a href="/login/">log in</a> to continue.'}
            raise HTTPError(400, data=error_data)
        else:
            return False
    return True


def check_external_auth(user):
    if user:
        return not user.has_usable_password() and (
            'VERIFIED' in sum([list(each.values()) for each in user.external_identity.values()], [])
        )
    return False


@block_bing_preview
@collect_auth
@must_be_valid_project(preprints_valid=True, groups_valid=True)
def claim_user_registered(auth, node, **kwargs):
    """
    View that prompts user to enter their password in order to claim being a contributor on a project.
    A user must be logged in.
    """

    current_user = auth.user

    sign_out_url = cas.get_logout_url(service_url=cas.get_login_url(service_url=request.url))
    if not current_user:
        return redirect(sign_out_url)

    # Logged in user should not be a contributor the project
    if hasattr(node, 'is_contributor') and node.is_contributor(current_user):
        data = {
            'message_short': 'Already a contributor',
            'message_long': ('The logged-in user is already a contributor to this '
                'project. Would you like to <a href="{}">log out</a>?').format(sign_out_url)
        }
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=data)

    # Logged in user is already a member of the OSF Group
    if hasattr(node, 'is_member') and node.is_member(current_user):
        data = {
            'message_short': 'Already a member',
            'message_long': ('The logged-in user is already a member of this OSF Group. '
                'Would you like to <a href="{}">log out</a>?').format(sign_out_url)
        }
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=data)

    uid, pid, token = kwargs['uid'], kwargs['pid'], kwargs['token']
    unreg_user = OSFUser.load(uid)
    if not verify_claim_token(unreg_user, token, pid=node._primary_key):
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'The token in the URL is invalid or has expired.'
        }
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=error_data)

    # Store the unreg_user data on the session in case the user registers
    # a new account
    session.data['unreg_user'] = {
        'uid': uid, 'pid': pid, 'token': token
    }
    session.save()

    # If a user is already validated though external auth, it is OK to claim
    should_claim = check_external_auth(auth.user)
    form = PasswordForm(request.form)
    if request.method == 'POST':
        if form.validate():
            if current_user.check_password(form.password.data):
                should_claim = True
            else:
                status.push_status_message(language.LOGIN_FAILED, kind='warning', trust=False)
        else:
            forms.push_errors_to_status(form.errors)
    if should_claim:
        node.replace_contributor(old=unreg_user, new=current_user)
        node.save()
        if isinstance(node, OSFGroup):
            status.push_status_message(
                'You are now a member of this OSFGroup.',
                kind='success',
                trust=False
            )
        else:
            status.push_status_message(
                'You are now a contributor to this project.',
                kind='success',
                trust=False
            )
        return redirect(node.url)
    if is_json_request():
        form_ret = forms.utils.jsonify(form)
        user_ret = profile_utils.serialize_user(current_user, full=False)
    else:
        form_ret = form
        user_ret = current_user
    return {
        'form': form_ret,
        'user': user_ret,
        'signOutUrl': sign_out_url
    }


@user_registered.connect
def replace_unclaimed_user_with_registered(user):
    """Listens for the user_registered signal. If unreg_user is stored in the
    session, then the current user is trying to claim themselves as a contributor.
    Replaces the old, unregistered contributor with the newly registered
    account.

    """
    unreg_user_info = session.data.get('unreg_user')
    if unreg_user_info:
        unreg_user = OSFUser.load(unreg_user_info['uid'])
        pid = unreg_user_info['pid']
        node = AbstractNode.load(pid)
        node.replace_contributor(old=unreg_user, new=user)
        node.save()
        status.push_status_message(
            'Successfully claimed contributor.', kind='success', trust=False)


@block_bing_preview
@collect_auth
def claim_user_form(auth, **kwargs):
    """
    View for rendering the set password page for a claimed user.
    Must have ``token`` as a querystring argument.
    Renders the set password form, validates it, and sets the user's password.
    HTTP Method: GET, POST
    """

    uid, pid = kwargs['uid'], kwargs['pid']
    token = request.form.get('token') or request.args.get('token')
    user = OSFUser.load(uid)

    # If unregistered user is not in database, or url bears an invalid token raise HTTP 400 error
    if not user or not verify_claim_token(user, token, pid):
        error_data = {
            'message_short': 'Invalid url.',
            'message_long': 'Claim user does not exists, the token in the URL is invalid or has expired.'
        }
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=error_data)

    # If user is logged in, redirect to 're-enter password' page
    if auth.logged_in:
        return redirect(web_url_for('claim_user_registered',
            uid=uid, pid=pid, token=token))

    unclaimed_record = user.unclaimed_records[pid]
    user.fullname = unclaimed_record['name']
    user.update_guessed_names()
    # The email can be the original referrer email if no claimer email has been specified.
    claimer_email = unclaimed_record.get('claimer_email') or unclaimed_record.get('email')
    # If there is a registered user with this email, redirect to 're-enter password' page
    try:
        user_from_email = OSFUser.objects.get(emails__address=claimer_email.lower().strip()) if claimer_email else None
    except OSFUser.DoesNotExist:
        user_from_email = None
    if user_from_email and user_from_email.is_registered:
        return redirect(web_url_for('claim_user_registered', uid=uid, pid=pid, token=token))

    form = SetEmailAndPasswordForm(request.form, token=token)
    if request.method == 'POST':
        if not form.validate():
            forms.push_errors_to_status(form.errors)
        elif settings.RECAPTCHA_SITE_KEY and not validate_recaptcha(request.form.get('g-recaptcha-response'), remote_ip=request.remote_addr):
            status.push_status_message('Invalid captcha supplied.', kind='error')
        else:
            username, password = claimer_email, form.password.data
            if not username:
                raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
                    message_long='No email associated with this account. Please claim this '
                    'account on the project to which you were invited.'
                ))

            user.register(username=username, password=password, accepted_terms_of_service=form.accepted_terms_of_service.data)
            # Clear unclaimed records
            user.unclaimed_records = {}
            user.verification_key = generate_verification_key()
            user.save()
            # Authenticate user and redirect to project page
            status.push_status_message(language.CLAIMED_CONTRIBUTOR, kind='success', trust=True)
            # Redirect to CAS and authenticate the user with a verification key.
            provider = PreprintProvider.load(pid)
            redirect_url = None
            if provider:
                redirect_url = web_url_for('auth_login', next=provider.landing_url, _absolute=True)
            else:
                # Add related claimed tags to user
                _add_related_claimed_tag_to_user(pid, user)
                redirect_url = web_url_for('resolve_guid', guid=pid, _absolute=True)

            return redirect(cas.get_login_url(
                redirect_url,
                username=user.username,
                verification_key=user.verification_key
            ))

    return {
        'firstname': user.given_name,
        'email': claimer_email if claimer_email else '',
        'fullname': user.fullname,
        'form': forms.utils.jsonify(form) if is_json_request() else form,
        'osf_contact_email': settings.OSF_CONTACT_EMAIL,
    }


def _add_related_claimed_tag_to_user(pid, user):
    """
    Adds claimed tag to incoming users, depending on whether the resource has related source tags
    :param pid: guid of either the node or the preprint
    :param user: the claiming user
    """
    node = AbstractNode.load(pid)
    preprint = Preprint.load(pid)
    osf_claimed_tag, created = Tag.all_tags.get_or_create(name=provider_claimed_tag('osf'), system=True)
    if node:
        node_source_tags = node.all_tags.filter(name__icontains='source:', system=True)
        if node_source_tags.exists():
            for tag in node_source_tags:
                claimed_tag, created = Tag.all_tags.get_or_create(name=NODE_SOURCE_TAG_CLAIMED_TAG_RELATION[tag.name],
                                                                  system=True)
                user.add_system_tag(claimed_tag)
        else:
            user.add_system_tag(osf_claimed_tag)
    elif preprint:
        provider_id = preprint.provider._id
        preprint_claimed_tag, created = Tag.all_tags.get_or_create(name=provider_claimed_tag(provider_id, 'preprint'),
                                                                   system=True)
        user.add_system_tag(preprint_claimed_tag)


@must_be_valid_project
@must_have_permission(ADMIN)
@must_not_be_registration
def invite_contributor_post(node, **kwargs):
    """API view for inviting an unregistered user. Performs validation, but does not actually invite the user.

    Expects JSON arguments with 'fullname' (required) and email (not required).
    """
    fullname = request.json.get('fullname').strip()
    email = request.json.get('email')
    # Validate and sanitize inputs as needed. Email will raise error if invalid.
    fullname = sanitize.strip_html(fullname)
    if email:
        email = email.lower().strip()
        try:
            validate_email(email)
        except ValidationError as e:
            return {'status': 400, 'message': e.message}, 400

    if not fullname:
        return {'status': 400, 'message': 'Full name field cannot be empty'}, 400

    # Check if email is in the database
    user = get_user(email=email)
    if user:
        if node.is_contributor(user):
            msg = 'User with this email address is already a contributor to this project.'
            return {'status': 400, 'message': msg}, 400
        elif not user.is_confirmed:
            serialized = profile_utils.serialize_unregistered(fullname, email)
        else:
            serialized = profile_utils.add_contributor_json(user)
            # use correct display name
            serialized['fullname'] = fullname
            serialized['email'] = email
    else:
        # Create a placeholder
        serialized = profile_utils.serialize_unregistered(fullname, email)
    return {'status': 'success', 'contributor': serialized}


@must_be_contributor_or_public
def claim_user_post(node, **kwargs):
    """
    View for claiming a user from the X-editable form on a project page.

    :param node: the project node
    :return:
    """

    request_data = request.json

    # The unclaimed user
    unclaimed_user = OSFUser.load(request_data['pk'])
    unclaimed_data = unclaimed_user.get_unclaimed_record(node._primary_key)

    # Claimer is not logged in and submit her/his email through X-editable, stored in `request_data['value']`
    if 'value' in request_data:
        email = request_data['value'].lower().strip()
        claimer = get_user(email=email)
        # registered user
        if claimer and claimer.is_registered:
            send_claim_registered_email(claimer, unclaimed_user, node)
        # unregistered user
        else:
            send_claim_email(email, unclaimed_user, node, notify=True)
    # Claimer is logged in with confirmed identity stored in `request_data['claimerId']`
    elif 'claimerId' in request_data:
        claimer_id = request_data['claimerId']
        claimer = OSFUser.load(claimer_id)
        send_claim_registered_email(claimer, unclaimed_user, node)
        email = claimer.username
    else:
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST)

    return {
        'status': 'success',
        'email': email,
        'fullname': unclaimed_data['name']
    }
