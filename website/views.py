# -*- coding: utf-8 -*-
from __future__ import unicode_literals
import itertools
from rest_framework import status as http_status
import logging
import math
import os
import requests
from future.moves.urllib.parse import unquote

from django.apps import apps
from flask import request, send_from_directory, Response, stream_with_context

from framework import sentry
from framework.auth import Auth
from framework.auth.decorators import must_be_logged_in
from framework.auth.forms import SignInForm, ForgotPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.forms import utils as form_utils
from framework.routing import proxy_url
from website import settings
from website.institutions.views import serialize_institution

from osf import features
from osf.models import BaseFileNode, Guid, Institution, Preprint, AbstractNode, Node, Registration
from addons.osfstorage.models import Region

from website.settings import EXTERNAL_EMBER_APPS, PROXY_EMBER_APPS, EXTERNAL_EMBER_SERVER_TIMEOUT, DOMAIN
from website.ember_osf_web.decorators import ember_flag_is_active
from website.ember_osf_web.views import use_ember_app
from website.project.model import has_anonymous_link
from osf.utils import permissions

from api.waffle.utils import flag_is_active, storage_i18n_flag_active

logger = logging.getLogger(__name__)
preprints_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['preprints']['path']))
registries_dir = os.path.abspath(os.path.join(os.getcwd(), EXTERNAL_EMBER_APPS['registries']['path']))
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

def serialize_groups_for_summary(node):
    groups = node.osf_groups
    n_groups = len(groups)
    group_string = ''
    for index, group in enumerate(groups):
        if index == n_groups - 1:
            separator = ''
        elif index == n_groups - 2:
            separator = ' & '
        else:
            separator = ', '

        group_string = group_string + group.name + separator

    return group_string


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
            'is_supplemental_project': node.has_linked_published_preprints,
            'childExists': Node.objects.get_children(node, active=True).exists(),
            'is_admin': node.has_permission(user, permissions.ADMIN),
            'is_contributor': node.is_contributor(user),
            'is_contributor_or_group_member': node.is_contributor_or_group_member(user),
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
            'groups': serialize_groups_for_summary(node),
            'description': node.description if len(node.description) <= 150 else node.description[0:150] + '...',
        })
    else:
        summary['can_view'] = False

    return summary

def index():
    # Check if we're on an institution landing page
    institution = Institution.objects.filter(domains__icontains=request.host, is_deleted=False)
    if institution.exists():
        institution = institution.get()
        inst_dict = serialize_institution(institution)
        inst_dict.update({
            'redirect_url': '{}institutions/{}/'.format(DOMAIN, institution._id),
        })
        return inst_dict
    else:
        return use_ember_app()

def find_bookmark_collection(user):
    Collection = apps.get_model('osf.Collection')
    return Collection.objects.get(creator=user, deleted__isnull=True, is_bookmark_collection=True)

@must_be_logged_in
def dashboard(auth):
    return use_ember_app()


@must_be_logged_in
@ember_flag_is_active(features.EMBER_MY_PROJECTS)
def my_projects(auth):
    user = auth.user

    region_list = get_storage_region_list(user)

    bookmark_collection = find_bookmark_collection(user)
    my_projects_id = bookmark_collection._id
    return {'addons_enabled': user.get_addon_names(),
            'dashboard_id': my_projects_id,
            'storage_regions': region_list,
            'storage_flag_is_active': storage_i18n_flag_active(),
            }


def validate_page_num(page, pages):
    if page < 0 or (pages and page >= pages):
        raise HTTPError(http_status.HTTP_400_BAD_REQUEST, data=dict(
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
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
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
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
        referent = guid_object.referent
        if referent is None:
            logger.error('Referent of GUID {0} not found'.format(guid))
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)
        if not referent.deep_url:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)

        # Handle file `/download` shortcut with supported types.
        if suffix and suffix.rstrip('/').lower() == 'download':
            file_referent = None
            if isinstance(referent, Preprint) and referent.primary_file:
                file_referent = referent.primary_file
            elif isinstance(referent, BaseFileNode) and referent.is_file:
                file_referent = referent

            if file_referent:
                if isinstance(file_referent.target, Preprint) and not file_referent.target.is_published:
                    # TODO: Ideally, permissions wouldn't be checked here.
                    # This is necessary to prevent a logical inconsistency with
                    # the routing scheme - if a preprint is not published, only
                    # admins and moderators should be able to know it exists.
                    auth = Auth.from_kwargs(request.args.to_dict(), {})
                    # Check if user isn't a nonetype or that the user has admin/moderator/superuser permissions
                    if auth.user is None or not (auth.user.has_perm('view_submissions', file_referent.target.provider) or
                            file_referent.target.has_permission(auth.user, permissions.ADMIN)):
                        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

                # Extend `request.args` adding `action=download`.
                request.args = request.args.copy()
                request.args.update({'action': 'download'})
                # Do not include the `download` suffix in the url rebuild.
                url = _build_guid_url(unquote(file_referent.deep_url))
                return proxy_url(url)

        # Handle Ember Applications
        if isinstance(referent, Preprint):
            if referent.provider.domain_redirect_enabled:
                # This route should always be intercepted by nginx for the branded domain,
                # w/ the exception of `<guid>/download` handled above.
                return redirect(referent.absolute_url, http_status.HTTP_301_MOVED_PERMANENTLY)

            if PROXY_EMBER_APPS:
                resp = requests.get(EXTERNAL_EMBER_APPS['preprints']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
                return Response(stream_with_context(resp.iter_content()), resp.status_code)

            return send_from_directory(preprints_dir, 'index.html')

        if isinstance(referent, BaseFileNode) and referent.is_file and (getattr(referent.target, 'is_quickfiles', False)):
            if referent.is_deleted:
                raise HTTPError(http_status.HTTP_410_GONE)
            if PROXY_EMBER_APPS:
                resp = requests.get(EXTERNAL_EMBER_APPS['ember_osf_web']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
                return Response(stream_with_context(resp.iter_content()), resp.status_code)

            return send_from_directory(ember_osf_web_dir, 'index.html')

        if isinstance(referent, Registration) and (
                not suffix or suffix.rstrip('/').lower() in ('comments', 'links', 'components')
        ):
            if flag_is_active(request, features.EMBER_REGISTRIES_DETAIL_PAGE):
                # Route only the base detail view to ember
                if PROXY_EMBER_APPS:
                    resp = requests.get(EXTERNAL_EMBER_APPS['ember_osf_web']['server'], stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
                    return Response(stream_with_context(resp.iter_content()), resp.status_code)

                return send_from_directory(registries_dir, 'index.html')

        url = _build_guid_url(unquote(referent.deep_url), suffix)
        return proxy_url(url)

    # GUID not found; try lower-cased and redirect if exists
    guid_object_lower = Guid.load(guid.lower())
    if guid_object_lower:
        return redirect(
            _build_guid_url(guid.lower(), suffix)
        )

    # GUID not found
    raise HTTPError(http_status.HTTP_404_NOT_FOUND)


# Redirects #

# redirect osf.io/about/ to OSF wiki page osf.io/4znzp/wiki/home/
def redirect_about(**kwargs):
    return redirect('https://osf.io/4znzp/wiki/home/')

def redirect_help(**kwargs):
    return redirect('/faq/')

def redirect_faq(**kwargs):
    return redirect('https://help.osf.io/hc/en-us/articles/360019737894-FAQs')

# redirect osf.io/howosfworks to osf.io/getting-started/
def redirect_howosfworks(**kwargs):
    return redirect('/getting-started/')


# redirect osf.io/getting-started to https://openscience.zendesk.com/hc/en-us
def redirect_getting_started(**kwargs):
    return redirect('https://openscience.zendesk.com/hc/en-us')


# Redirect to home page
def redirect_to_home():
    return redirect('/')


def redirect_to_cos_news(**kwargs):
    # Redirect to COS News page
    return redirect('https://cos.io/news/')


# Return error for legacy SHARE v1 search route
def legacy_share_v1_search(**kwargs):
    return HTTPError(
        http_status.HTTP_400_BAD_REQUEST,
        data=dict(
            message_long='Please use v2 of the SHARE search API available at {}api/v2/share/search/creativeworks/_search.'.format(settings.SHARE_URL)
        )
    )


def get_storage_region_list(user, node=False):
    if not user:  # Preserves legacy frontend test behavior
        return []

    if node:
        default_region = node.osfstorage_region
    else:
        default_region = user.get_addon('osfstorage').default_region

    available_regions = list(Region.objects.order_by('name').values('_id', 'name'))
    default_region = {'name': default_region.name, '_id': default_region._id}
    available_regions.insert(0, available_regions.pop(available_regions.index(default_region)))  # default should be at top of list for UI.

    return available_regions
