# -*- coding: utf-8 -*-
import itertools
import httplib as http
import logging
import math
import os
import requests
import urllib

from django.apps import apps
from django.db.models import Count
from flask import request, send_from_directory, Response, stream_with_context

from framework import sentry
from framework.auth import Auth
from framework.auth.decorators import must_be_logged_in
from framework.auth.decorators import email_required
from framework.auth.forms import SignInForm, ForgotPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.forms import utils as form_utils
from framework.routing import proxy_url
from framework.auth.core import get_current_user_id
from website import settings
from website.institutions.views import serialize_institution

from osf.models import BaseFileNode, Guid, Institution, PreprintService, AbstractNode, Node
from website.settings import EXTERNAL_EMBER_APPS, PROXY_EMBER_APPS, EXTERNAL_EMBER_SERVER_TIMEOUT, INSTITUTION_DISPLAY_NODE_THRESHOLD, DOMAIN
from website.project.model import has_anonymous_link
from website.util import permissions

logger = logging.getLogger(__name__)
preprints_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['preprints']['path']))
ember_osf_web_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['ember_osf_web']['path']))

def serialize_contributors_for_summary(node, max_count=3):
    # # TODO: Use .filter(visible=True) when chaining is fixed in django-include
    users = [contrib.user for contrib in node.contributor_set.all() if contrib.visible]
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
        contributor = user.get_summary(formatter='surname')
        contributor['user_id'] = user._primary_key
        contributor['separator'] = separator

        contributors.append(contributor)

    return {
        'contributors': contributors,
        'others_count': others_count,
    }


def serialize_node_summary(node, auth, primary=True, show_path=False):
    is_registration = node.is_registration
    summary = {
        'id': node._id,
        'primary': primary,
        'is_registration': node.is_registration,
        'is_fork': node.is_fork,
        'is_pending_registration': node.is_pending_registration if is_registration else False,
        'is_retracted': node.is_retracted if is_registration else False,
        'is_pending_retraction': node.is_pending_retraction if is_registration else False,
        'embargo_end_date': node.embargo_end_date.strftime('%A, %b. %d, %Y') if is_registration and node.embargo_end_date else False,
        'is_pending_embargo': node.is_pending_embargo if is_registration else False,
        'is_embargoed': node.is_embargoed if is_registration else False,
        'archiving': node.archiving if is_registration else False,
    }

    parent_node = node.parent_node
    user = auth.user
    if node.can_view(auth):
        # Re-query node with contributor guids included to prevent N contributor queries
        node = AbstractNode.objects.filter(pk=node.pk).include('contributor__user__guids').get()
        contributor_data = serialize_contributors_for_summary(node)
        summary.update({
            'can_view': True,
            'can_edit': node.can_edit(auth),
            'primary_id': node._id,
            'url': node.url,
            'primary': primary,
            'api_url': node.api_url,
            'title': node.title,
            'category': node.category,
            'isPreprint': bool(node.preprint_file_id),
            'childExists': Node.objects.get_children(node, active=True).exists(),
            'is_admin': node.has_permission(user, permissions.ADMIN),
            'is_contributor': node.is_contributor(user),
            'logged_in': auth.logged_in,
            'node_type': node.project_or_component,
            'is_fork': node.is_fork,
            'is_registration': is_registration,
            'anonymous': has_anonymous_link(node, auth),
            'registered_date': node.registered_date.strftime('%Y-%m-%d %H:%M UTC')
            if node.is_registration
            else None,
            'forked_date': node.forked_date.strftime('%Y-%m-%d %H:%M UTC')
            if node.is_fork
            else None,
            'ua_count': None,
            'ua': None,
            'non_ua': None,
            'is_public': node.is_public,
            'parent_title': parent_node.title if parent_node else None,
            'parent_is_public': parent_node.is_public if parent_node else False,
            'show_path': show_path,
            'contributors': contributor_data['contributors'],
            'others_count': contributor_data['others_count'],
            'description': node.description if len(node.description) <= 150 else node.description[0:150] + '...',
        })
    else:
        summary['can_view'] = False

    return summary


@email_required
def index():
    try:  # Check if we're on an institution landing page
        #TODO : make this way more robust
        institution = Institution.objects.get(domains__contains=[request.host.lower()], is_deleted=False)
        inst_dict = serialize_institution(institution)
        inst_dict.update({
            'home': False,
            'institution': True,
            'redirect_url': '{}institutions/{}/'.format(DOMAIN, institution._id),
        })

        return inst_dict
    except Institution.DoesNotExist:
        pass

    user_id = get_current_user_id()
    if user_id:  # Logged in: return either landing page or user home page
        all_institutions = (
            Institution.objects.filter(
                is_deleted=False,
                nodes__is_public=True,
                nodes__is_deleted=False,
                nodes__type='osf.node'
            )
            .annotate(Count('nodes'))
            .filter(nodes__count__gte=INSTITUTION_DISPLAY_NODE_THRESHOLD)
            .order_by('name').only('_id', 'name', 'logo_name')
        )
        dashboard_institutions = [
            {'id': inst._id, 'name': inst.name, 'logo_path': inst.logo_path_rounded_corners}
            for inst in all_institutions
        ]

        # generation key check
        key_exists_check = userkey_generation_check(user_id)

        if not key_exists_check:
            userkey_generation(user_id)       

        return {
            'home': True,
            'dashboard_institutions': dashboard_institutions,
        }
    else:  # Logged out: return landing page
        return {
            'home': True,
        }


def find_bookmark_collection(user):
    Collection = apps.get_model('osf.Collection')
    return Collection.objects.get(creator=user, is_deleted=False, is_bookmark_collection=True)

@must_be_logged_in
def dashboard(auth):
    return redirect('/')


@must_be_logged_in
def my_projects(auth):
    user = auth.user
    bookmark_collection = find_bookmark_collection(user)
    my_projects_id = bookmark_collection._id
    return {'addons_enabled': user.get_addon_names(),
            'dashboard_id': my_projects_id,
            }


def validate_page_num(page, pages):
    if page < 0 or (pages and page >= pages):
        raise HTTPError(http.BAD_REQUEST, data=dict(
            message_long='Invalid value for "page".'
        ))


def paginate(items, total, page, size):
    pages = math.ceil(total / float(size))
    validate_page_num(page, pages)

    start = page * size
    paginated_items = itertools.islice(items, start, start + size)

    return paginated_items, pages


def reproducibility():
    return redirect('/ezcuj/wiki')


def signin_form():
    return form_utils.jsonify(SignInForm())


def forgot_password_form():
    return form_utils.jsonify(ForgotPasswordForm(prefix='forgot_password'))


# GUID ###

def _build_guid_url(base, suffix=None):
    url = '/'.join([
        each.strip('/') for each in [base, suffix]
        if each
    ])
    if not isinstance(url, unicode):
        url = url.decode('utf-8')
    return u'/{0}/'.format(url)


def resolve_guid_download(guid, suffix=None, provider=None):
    return resolve_guid(guid, suffix='download')


def resolve_guid(guid, suffix=None):
    """Load GUID by primary key, look up the corresponding view function in the
    routing table, and return the return value of the view function without
    changing the URL.

    :param str guid: GUID primary key
    :param str suffix: Remainder of URL after the GUID
    :return: Return value of proxied view function
    """
    try:
        # Look up
        guid_object = Guid.load(guid)
    except KeyError as e:
        if e.message == 'osfstorageguidfile':  # Used when an old detached OsfStorageGuidFile object is accessed
            raise HTTPError(http.NOT_FOUND)
        else:
            raise e
    if guid_object:
        # verify that the object implements a GuidStoredObject-like interface. If a model
        #   was once GuidStoredObject-like but that relationship has changed, it's
        #   possible to have referents that are instances of classes that don't
        #   have a deep_url attribute or otherwise don't behave as
        #   expected.
        if not hasattr(guid_object.referent, 'deep_url'):
            sentry.log_message(
                'Guid resolved to an object with no deep_url', dict(guid=guid)
            )
            raise HTTPError(http.NOT_FOUND)
        referent = guid_object.referent
        if referent is None:
            logger.error('Referent of GUID {0} not found'.format(guid))
            raise HTTPError(http.NOT_FOUND)
        if not referent.deep_url:
            raise HTTPError(http.NOT_FOUND)

        # Handle file `/download` shortcut with supported types.
        if suffix and suffix.rstrip('/').lower() == 'download':
            file_referent = None
            if isinstance(referent, PreprintService) and referent.primary_file:
                if not referent.is_published:
                    # TODO: Ideally, permissions wouldn't be checked here.
                    # This is necessary to prevent a logical inconsistency with
                    # the routing scheme - if a preprint is not published, only
                    # admins should be able to know it exists.
                    auth = Auth.from_kwargs(request.args.to_dict(), {})
                    if not referent.node.has_permission(auth.user, permissions.ADMIN):
                        raise HTTPError(http.NOT_FOUND)
                file_referent = referent.primary_file
            elif isinstance(referent, BaseFileNode) and referent.is_file:
                file_referent = referent

            if file_referent:
                # Extend `request.args` adding `action=download`.
                request.args = request.args.copy()
                request.args.update({'action': 'download'})
                # Do not include the `download` suffix in the url rebuild.
                url = _build_guid_url(urllib.unquote(file_referent.deep_url))
                return proxy_url(url)

        if suffix and suffix.rstrip('/').lower() == 'addtimestamp':
            file_referent = None
            if isinstance(referent, PreprintService) and referent.primary_file:
                if not referent.is_published:
                    # TODO: Ideally, permissions wouldn't be checked here.
                    # This is necessary to prevent a logical inconsistency with
                    # the routing scheme - if a preprint is not published, only
                    # admins should be able to know it exists.
                    auth = Auth.from_kwargs(request.args.to_dict(), {})
                    if not referent.node.has_permission(auth.user, permissions.ADMIN):
                        raise HTTPError(http.NOT_FOUND)
                file_referent = referent.primary_file
            elif isinstance(referent, BaseFileNode) and referent.is_file:
                file_referent = referent

            if file_referent:
                # Extend `request.args` adding `action=addtimestamp`.
                request.args = request.args.copy()
                request.args.update({'action': 'addtimestamp'})
                # Do not include the `addtimestamp` suffix in the url rebuild.
                # Do not include the `addtimestamp` suffix in the url rebuild.
                url = _build_guid_url(urllib.unquote(file_referent.deep_url))
                return proxy_url(url)
        elif suffix and suffix.rstrip('/').split('/')[-1].lower() == 'addtimestamp':
            # Extend `request.args` adding `action=addtimestamp`.
            request.args = request.args.copy()
            request.args.update({'action': 'addtimestamp'})
            # Do not include the `addtimestamp` suffix in the url rebuild.
            # Do not include the `addtimestamp` suffix in the url rebuild.
            url = _build_guid_url(urllib.unquote(referent.deep_url), suffix.split('/')[0])
            return proxy_url(url)

        if isinstance(referent, PreprintService):
            if referent.provider.domain_redirect_enabled:
                # This route should always be intercepted by nginx for the branded domain,
                # w/ the exception of `<guid>/download` handled above.
                return redirect(referent.absolute_url, http.MOVED_PERMANENTLY)

            if PROXY_EMBER_APPS:
                resp = requests.get(EXTERNAL_EMBER_APPS['preprints']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
                return Response(stream_with_context(resp.iter_content()), resp.status_code)

            return send_from_directory(preprints_dir, 'index.html')

        if isinstance(referent, BaseFileNode) and referent.is_file and referent.node.is_quickfiles:
            if referent.is_deleted:
                raise HTTPError(http.GONE)
            if PROXY_EMBER_APPS:
                resp = requests.get(EXTERNAL_EMBER_APPS['ember_osf_web']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
                return Response(stream_with_context(resp.iter_content()), resp.status_code)

            return send_from_directory(ember_osf_web_dir, 'index.html')

        url = _build_guid_url(urllib.unquote(referent.deep_url), suffix)
        return proxy_url(url)

    # GUID not found; try lower-cased and redirect if exists
    guid_object_lower = Guid.load(guid.lower())
    if guid_object_lower:
        return redirect(
            _build_guid_url(guid.lower(), suffix)
        )

    # GUID not found
    raise HTTPError(http.NOT_FOUND)


# Redirects #

# redirect osf.io/about/ to OSF wiki page osf.io/4znzp/wiki/home/
def redirect_about(**kwargs):
    return redirect('https://osf.io/4znzp/wiki/home/')

def redirect_help(**kwargs):
    return redirect('/faq/')

def redirect_faq(**kwargs):
    return redirect('http://help.osf.io/m/faqs/')

# redirect osf.io/howosfworks to osf.io/getting-started/
def redirect_howosfworks(**kwargs):
    return redirect('/getting-started/')


# redirect osf.io/getting-started to help.osf.io/
def redirect_getting_started(**kwargs):
    return redirect('http://help.osf.io/')


# Redirect to home page
def redirect_to_home():
    return redirect('/')


def redirect_to_cos_news(**kwargs):
    # Redirect to COS News page
    return redirect('https://cos.io/news/')


# Return error for legacy SHARE v1 search route
def legacy_share_v1_search(**kwargs):
    return HTTPError(
        http.BAD_REQUEST,
        data=dict(
            message_long='Please use v2 of the SHARE search API available at {}api/v2/share/search/creativeworks/_search.'.format(settings.SHARE_URL)
        )
    )

# userkey generation check
def userkey_generation_check(guid):
    from osf.models import RdmUserKey

    logger.info(' userkey_generation_check ')
    # no user_key_info
    if not RdmUserKey.objects.filter(guid=Guid.objects.get(_id=guid).object_id).exists():
        return False

    return True

# userkey generation
def userkey_generation(guid):
    logger.info('userkey_generation guid:' + guid)
    from api.timestamp import local
    from osf.models import RdmUserKey
    import os.path
    import subprocess
    from datetime import datetime
    import hashlib

    try:
       generation_date = datetime.now()
       generation_date_str = generation_date.strftime('%Y%m%d%H%M%S')
       generation_date_hash = hashlib.md5(generation_date_str).hexdigest()
       generation_pvt_key_name = local.KEY_NAME_FORMAT.format(guid, generation_date_hash,
                                                                   local.KEY_NAME_PRIVATE, local.KEY_EXTENSION)
       generation_pub_key_name = local.KEY_NAME_FORMAT.format(guid, generation_date_hash,
                                                                   local.KEY_NAME_PUBLIC, local.KEY_EXTENSION)
       # private key generation
       pvt_key_generation_cmd = [local.OPENSSL_MAIN_CMD, local.OPENSSL_OPTION_GENRSA,
                                     local.OPENSSL_OPTION_OUT,
                                     os.path.join(local.KEY_SAVE_PATH, generation_pvt_key_name),
                                     local.KEY_BIT_VALUE]

       pub_key_generation_cmd = [local.OPENSSL_MAIN_CMD, local.OPENSSL_OPTION_RSA,
                                     local.OPENSSL_OPTION_IN,
                                     os.path.join(local.KEY_SAVE_PATH, generation_pvt_key_name),
                                     local.OPENSSL_OPTION_PUBOUT, local.OPENSSL_OPTION_OUT,
                                     os.path.join(local.KEY_SAVE_PATH, generation_pub_key_name)]

       prc = subprocess.Popen(pvt_key_generation_cmd, shell=False,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              stdout=subprocess.PIPE)

       stdout_data, stderr_data = prc.communicate()

       prc = subprocess.Popen(pub_key_generation_cmd, shell=False,
                              stdin=subprocess.PIPE,
                              stderr=subprocess.PIPE,
                              stdout=subprocess.PIPE)

       stdout_data, stderr_data = prc.communicate()

       pvt_userkey_info = create_rdmuserkey_info(Guid.objects.get(_id=guid).object_id
                                                 , generation_pvt_key_name
                                                 , local.PRIVATE_KEY_VALUE
                                                 , generation_date)

       pub_userkey_info = create_rdmuserkey_info(Guid.objects.get(_id=guid).object_id
                                                 , generation_pub_key_name
                                                 , local.PUBLIC_KEY_VALUE
                                                 , generation_date)

       pvt_userkey_info.save()
       pub_userkey_info.save()

    except Exception as error:
       logger.exception(error)

def create_rdmuserkey_info(user_id, key_name, key_kind, date):
    from osf.models import RdmUserKey

    userkey_info = RdmUserKey()
    userkey_info.guid = user_id
    userkey_info.key_name = key_name
    userkey_info.key_kind = key_kind
    userkey_info.created_time = date

    return userkey_info
