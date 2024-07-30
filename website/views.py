from furl import furl
import waffle
import itertools
from rest_framework import status as http_status
import logging
import math
import os
import requests
from urllib.parse import unquote

from django.apps import apps
from flask import request, send_from_directory, Response, stream_with_context

from framework.auth import Auth
from framework.auth.decorators import must_be_logged_in
from framework.auth.forms import SignInForm, ForgotPasswordForm
from framework.exceptions import HTTPError
from framework.flask import redirect  # VOL-aware redirect
from framework.forms import utils as form_utils
from framework.routing import proxy_url
from website import settings

from addons.osfstorage.models import Region, OsfStorageFile

from osf import features, exceptions
from osf.models import Guid, Preprint, AbstractNode, Node, DraftNode, Registration, BaseFileNode

from website.settings import EXTERNAL_EMBER_APPS, PROXY_EMBER_APPS, EXTERNAL_EMBER_SERVER_TIMEOUT, DOMAIN
from website.ember_osf_web.decorators import ember_flag_is_active
from website.ember_osf_web.views import use_ember_app
from website.project.decorators import check_contributor_auth
from website.project.model import has_anonymous_link
from osf.utils import permissions
from osf.metadata.tools import pls_gather_metadata_file

from api.waffle.utils import storage_i18n_flag_active

logger = logging.getLogger(__name__)
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
        node = AbstractNode.objects.filter(pk=node.pk).prefetch_related('contributor_set__user__guids').get()
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


def resolve_guid_download(guid, provider=None):
    try:
        guid = Guid.objects.get(_id=guid.lower())
    except Guid.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    resource = guid.referent

    suffix = request.view_args.get('suffix')
    if suffix and suffix.startswith('osfstorage/files/'):  # legacy route
        filename = suffix.replace('osfstorage/files/', '').rstrip('/')
        if '/' in filename:  # legacy behavior
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)

        try:
            file_path = resource.files.get(name=filename)._id
        except OsfStorageFile.DoesNotExist:
            raise HTTPError(http_status.HTTP_404_NOT_FOUND)

        return redirect(
            resource.web_url_for(
                'addon_view_or_download_file',
                path=file_path,
                action='download',
                provider='osfstorage',
            ), code=http_status.HTTP_301_MOVED_PERMANENTLY
        )

    if isinstance(resource, Preprint):
        if not resource.is_published:
            auth = Auth.from_kwargs(request.args.to_dict(), {})
            # Check if user isn't a nonetype or that the user has admin/moderator/superuser permissions
            if auth.user is None:
                raise HTTPError(http_status.HTTP_404_NOT_FOUND)
            if not (auth.user.has_perm('view_submissions', resource.provider) or
                    resource.has_permission(auth.user, permissions.ADMIN)):
                raise HTTPError(http_status.HTTP_404_NOT_FOUND)
        resource = resource.primary_file

    request.args = request.args.copy()
    if 'revision' not in request.args:  # This is to maintain legacy behavior
        request.args.update({'action': 'download'})

    return proxy_url(_build_guid_url(unquote(resource.deep_url)))


def stream_emberapp(server, directory):
    if PROXY_EMBER_APPS:
        resp = requests.get(server, stream=True, timeout=EXTERNAL_EMBER_SERVER_TIMEOUT)
        return Response(stream_with_context(resp.iter_content()), resp.status_code)
    return send_from_directory(directory, 'index.html')


def _build_guid_url(base, suffix=None):
    url = '/'.join([
        each.strip('/') for each in [base, suffix]
        if each
    ])
    if not isinstance(url, str):
        url = url.decode('utf-8')
    return f'/{url}/'


def resolve_guid(guid, suffix=None):
    '''
    This function is supposed to resolve a guid to a specific page of the OSF some pages are "legacy pages" that use v1
    endpoints to serve pages from django, some page are new "emberized" pages only available via the ember app.
    Preprints for example are served from the external emberapp and streamed into Django and on to the user, while Wikis
    are served via a `/v1` endpoint, the `deep_url` for that resource.

    There are also additional routes in this fintion that lead to legacies views that serve bytes for that files guid,
    for example the url `/<file-guid>/?action=download` a response for file data is served.
    '''

    clean_suffix = (
        suffix.rstrip('/').lower()
        if suffix
        else ''
    )

    # Legacies views that serve bytes
    if 'download' == clean_suffix:
        return resolve_guid_download(guid)
    if 'download' == request.args.get('action'):
        return resolve_guid_download(guid)
    if 'revision' in request.args:
        return resolve_guid_download(guid)

    # Retrieve guid data if present, error if missing
    try:
        resource = Guid.objects.get(_id=guid.lower()).referent
    except Guid.DoesNotExist:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    if not resource or not resource.deep_url:
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    if isinstance(resource, DraftNode):
        raise HTTPError(http_status.HTTP_404_NOT_FOUND)

    if isinstance(resource, AbstractNode):
        login_redirect_response = check_contributor_auth(
            resource,
            auth=Auth.from_kwargs(request.args.to_dict(), {}),
            include_public=True,
            include_view_only_anon=True,
            include_groups=True
        )
        if login_redirect_response:
            return login_redirect_response

    if clean_suffix == 'metadata':
        format_arg = request.args.get('format')
        if format_arg:
            return guid_metadata_download(guid, resource, format_arg)
        else:
            return use_ember_app()

    # Stream to ember app if resource has emberized view
    addon_paths = [f'files/{addon.short_name}' for addon in settings.ADDONS_AVAILABLE_DICT.values() if 'storage' in addon.categories] + ['files']

    if isinstance(resource, Preprint):
        if resource.provider.domain_redirect_enabled:
            return redirect(resource.absolute_url, http_status.HTTP_301_MOVED_PERMANENTLY)
        return use_ember_app()

    elif isinstance(resource, Registration) and (clean_suffix in ('', 'comments', 'links', 'components', 'resources',)) and waffle.flag_is_active(request, features.EMBER_REGISTRIES_DETAIL_PAGE):
        return use_ember_app()

    elif isinstance(resource, Registration) and clean_suffix and clean_suffix.startswith('metadata') and waffle.flag_is_active(request, features.EMBER_REGISTRIES_DETAIL_PAGE):
        return use_ember_app()

    elif isinstance(resource, Registration) and (clean_suffix in ('files', 'files/osfstorage')) and waffle.flag_is_active(request, features.EMBER_REGISTRATION_FILES):
        return use_ember_app()

    elif isinstance(resource, Node) and clean_suffix and any(path.startswith(clean_suffix) for path in addon_paths) and waffle.flag_is_active(request, features.EMBER_PROJECT_FILES):
        return use_ember_app()

    elif isinstance(resource, Node) and clean_suffix and clean_suffix.startswith('metadata'):
        return use_ember_app()

    elif isinstance(resource, BaseFileNode) and resource.is_file and not isinstance(resource.target, Preprint):
        if isinstance(resource.target, Registration) and waffle.flag_is_active(request, features.EMBER_FILE_REGISTRATION_DETAIL):
            return use_ember_app()
        if isinstance(resource.target, Node) and waffle.flag_is_active(request, features.EMBER_FILE_PROJECT_DETAIL):
            return use_ember_app()

    # Redirect to legacy endpoint for Nodes, Wikis etc.
    url = _build_guid_url(unquote(resource.deep_url), suffix)
    return proxy_url(url)

# Redirects #

# redirect osf.io/about/ to OSF wiki page osf.io/4znzp/wiki/home/
def redirect_about(**kwargs):
    return redirect('https://osf.io/4znzp/wiki/home/')

def redirect_help(**kwargs):
    return redirect('/faq/')

def redirect_faq(**kwargs):
    return redirect('https://help.osf.io/article/406-faqs-home-page')

# redirect osf.io/howosfworks to osf.io/getting-started/
def redirect_howosfworks(**kwargs):
    return redirect('/getting-started/')


# redirect osf.io/getting-started to https://help.osf.io/article/342-getting-started-on-the-osf
def redirect_getting_started(**kwargs):
    return redirect('https://help.osf.io/article/342-getting-started-on-the-osf')


# Redirect to home page
def redirect_to_home():
    return redirect('/')


def redirect_to_cos_news(**kwargs):
    # Redirect to COS News page
    return redirect('https://cos.io/news/')


def redirect_to_registration_workflow(**kwargs):
    # Redirect to making new registration
    return redirect(furl(DOMAIN).add(path='registries/osf/new').url)


# Return error for legacy SHARE v1 search route
def legacy_share_v1_search(**kwargs):
    return HTTPError(
        http_status.HTTP_400_BAD_REQUEST,
        data=dict(
            message_long=f'Please use v2 of the SHARE search API available at {settings.SHARE_URL}api/v2/share/search/creativeworks/_search.'
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


def guid_metadata_download(guid, resource, metadata_format):
    try:
        result = pls_gather_metadata_file(resource, metadata_format)
    except exceptions.InvalidMetadataFormat as error:
        raise HTTPError(
            http_status.HTTP_400_BAD_REQUEST,
            data={'message_long': error.message},
        )
    else:
        return Response(
            result.serialized_metadata,
            content_type=result.mediatype,
            headers={
                'Content-Disposition': f'attachment; filename={result.filename}',
            },
        )
