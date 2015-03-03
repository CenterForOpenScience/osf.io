# -*- coding: utf-8 -*-
import httplib as http
import os

from flask import send_from_directory

from framework import status
from framework import sentry
from framework.routing import Rule
from framework.flask import redirect
from framework.routing import WebRenderer
from framework.exceptions import HTTPError
from framework.auth import get_display_name
from framework.routing import json_renderer
from framework.routing import process_rules
from framework.auth import views as auth_views
from framework.routing import render_mako_string
from framework.auth.core import _get_current_user

from website import util
from website import settings
from website import language
from website.util import paths
from website.util import sanitize
from website import landing_pages as landing_page_views
from website import views as website_views
from website.citations import views as citation_views
from website.search import views as search_views
from website.oauth import views as oauth_views
from website.profile import views as profile_views
from website.project import views as project_views
from website.addons.base import views as addon_views
from website.discovery import views as discovery_views
from website.conferences import views as conference_views
from website.notifications import views as notification_views


def get_globals():
    """Context variables that are available for every template rendered by
    OSFWebRenderer.
    """
    user = _get_current_user()
    return {
        'user_name': user.username if user else '',
        'user_full_name': user.fullname if user else '',
        'user_id': user._primary_key if user else '',
        'user_url': user.url if user else '',
        'user_gravatar': profile_views.current_user_gravatar(size=25)['gravatar_url'] if user else '',
        'user_api_url': user.api_url if user else '',
        'display_name': get_display_name(user.fullname) if user else '',
        'use_cdn': settings.USE_CDN_FOR_CLIENT_LIBS,
        'piwik_host': settings.PIWIK_HOST,
        'piwik_site_id': settings.PIWIK_SITE_ID,
        'sentry_dsn_js': settings.SENTRY_DSN_JS if sentry.enabled else None,
        'dev_mode': settings.DEV_MODE,
        'allow_login': settings.ALLOW_LOGIN,
        'cookie_name': settings.COOKIE_NAME,
        'status': status.pop_status_messages(),
        'domain': settings.DOMAIN,
        'disk_saving_mode': settings.DISK_SAVING_MODE,
        'language': language,
        'web_url_for': util.web_url_for,
        'api_url_for': util.api_url_for,
        'sanitize': sanitize,
        'js_str': lambda x: x.replace("'", r"\'").replace('"', r'\"'),
        'webpack_asset': paths.webpack_asset,
        'waterbutler_url': settings.WATERBUTLER_URL
    }


class OsfWebRenderer(WebRenderer):

    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)

#: Use if a view only redirects or raises error
notemplate = OsfWebRenderer('', render_mako_string)


# Static files (robots.txt, etc.)

def favicon():
    return send_from_directory(
        settings.STATIC_FOLDER,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


def robots():
    """Serves the robots.txt file."""
    # Allow local robots.txt
    if os.path.exists(os.path.join(settings.STATIC_FOLDER,
                                   'robots.local.txt')):
        robots_file = 'robots.local.txt'
    else:
        robots_file = 'robots.txt'
    return send_from_directory(
        settings.STATIC_FOLDER,
        robots_file,
        mimetype='text/plain'
    )


def goodbye():
    # Redirect to dashboard if logged in
    if _get_current_user():
        return redirect(util.web_url_for('dashboard'))
    status.push_status_message(language.LOGOUT, 'info')
    return {}


def make_url_map(app):
    '''Set up all the routes for the OSF app.

    :param app: A Flask/Werkzeug app to bind the rules to.
    '''

    # Set default views to 404, using URL-appropriate renderers
    process_rules(app, [
        Rule('/<path:_>', ['get', 'post'], HTTPError(http.NOT_FOUND),
             OsfWebRenderer('', render_mako_string)),
        Rule('/api/v1/<path:_>', ['get', 'post'],
             HTTPError(http.NOT_FOUND), json_renderer),
    ])

    ### GUID ###
    process_rules(app, [

        Rule(
            [
                '/<guid>/',
                '/<guid>/<path:suffix>',
            ],
            ['get', 'post', 'put', 'patch', 'delete'],
            website_views.resolve_guid,
            OsfWebRenderer('', render_mako_string),
        ),

        Rule(
            [
                '/api/v1/<guid>/',
                '/api/v1/<guid>/<path:suffix>',
            ],
            ['get', 'post', 'put', 'patch', 'delete'],
            website_views.resolve_guid,
            json_renderer,
        ),

    ])

    # Static files
    process_rules(app, [
        Rule('/favicon.ico', 'get', favicon, json_renderer),
        Rule('/robots.txt', 'get', robots, json_renderer),
    ])

    ### Base ###

    process_rules(app, [

        Rule('/dashboard/', 'get', website_views.dashboard, OsfWebRenderer('dashboard.mako')),
        Rule('/reproducibility/', 'get',
             website_views.reproducibility, OsfWebRenderer('', render_mako_string)),

        Rule('/about/', 'get', {}, OsfWebRenderer('public/pages/about.mako')),
        Rule('/howosfworks/', 'get', {}, OsfWebRenderer('public/pages/howosfworks.mako')),
        Rule('/faq/', 'get', {}, OsfWebRenderer('public/pages/faq.mako')),
        Rule('/getting-started/', 'get', {}, OsfWebRenderer('public/pages/getting_started.mako')),
        Rule('/explore/', 'get', {}, OsfWebRenderer('public/explore.mako')),
        Rule(['/messages/', '/help/'], 'get', {}, OsfWebRenderer('public/comingsoon.mako')),

        Rule(
            '/view/<meeting>/',
            'get',
            conference_views.conference_results,
            OsfWebRenderer('public/pages/meeting.mako'),
        ),

        Rule(
            '/view/<meeting>/plain/',
            'get',
            conference_views.conference_results,
            OsfWebRenderer('public/pages/meeting_plain.mako'),
            endpoint_suffix='__plain',
        ),

        Rule(
            '/api/v1/view/<meeting>/',
            'get',
            conference_views.conference_data,
            json_renderer,
        ),

        Rule(
            '/presentations/',
            'get',
            conference_views.conference_view,
            OsfWebRenderer('public/pages/meeting_landing.mako'),
        ),

        Rule('/news/', 'get', {}, OsfWebRenderer('public/pages/news.mako')),

    ])

    # Site-wide API routes

    process_rules(app, [
        Rule(
            '/citations/styles/',
            'get',
            citation_views.list_citation_styles,
            json_renderer,
        ),
    ], prefix='/api/v1')

    process_rules(app, [
        Rule(
            [
                '/project/<pid>/<addon>/settings/disable/',
                '/project/<pid>/node/<nid>/<addon>/settings/disable/',
            ],
            'post',
            addon_views.disable_addon,
            json_renderer,
        ),

        Rule(
            '/profile/<uid>/<addon>/settings/',
            'get',
            addon_views.get_addon_user_config,
            json_renderer,
        ),
    ], prefix='/api/v1')

    # OAuth

    process_rules(app, [
        Rule(
            '/oauth/connect/<service_name>/',
            'get',
            oauth_views.oauth_connect,
            json_renderer,
        ),

        Rule(
            '/oauth/callback/<service_name>/',
            'get',
            oauth_views.oauth_callback,
            OsfWebRenderer('util/oauth_complete.mako'),
        ),
    ])

    process_rules(app, [
        Rule(
            [
                '/oauth/accounts/<external_account_id>/',
            ],
            'delete',
            oauth_views.oauth_disconnect,
            json_renderer,
        )
    ], prefix='/api/v1')

    process_rules(app, [
        Rule('/dashboard/get_nodes/', 'get', website_views.get_dashboard_nodes, json_renderer),
        Rule(
            [
                '/dashboard/<nid>',
                '/dashboard/',
            ],
            'get', website_views.get_dashboard, json_renderer),
    ], prefix='/api/v1')

    ### Meta-data ###

    process_rules(app, [

        Rule(
            [
                '/project/<pid>/comments/',
                '/project/<pid>/node/<nid>/comments/',
            ],
            'get',
            project_views.comment.list_comments,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comments/discussion/',
                '/project/<pid>/node/<nid>/comments/discussion/',
            ],
            'get',
            project_views.comment.comment_discussion,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/',
                '/project/<pid>/node/<nid>/comment/',
            ],
            'post',
            project_views.comment.add_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/',
                '/project/<pid>/node/<nid>/comment/<cid>/',
            ],
            'put',
            project_views.comment.edit_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/',
                '/project/<pid>/node/<nid>/comment/<cid>/',
            ],
            'delete',
            project_views.comment.delete_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/undelete/',
                '/project/<pid>/node/<nid>/comment/<cid>/undelete/',
            ],
            'put',
            project_views.comment.undelete_comment,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comments/timestamps/',
                '/project/<pid>/node/<nid>/comments/timestamps/',
            ],
            'put',
            project_views.comment.update_comments_timestamp,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/report/',
                '/project/<pid>/node/<nid>/comment/<cid>/report/',
            ],
            'post',
            project_views.comment.report_abuse,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/comment/<cid>/unreport/',
                '/project/<pid>/node/<nid>/comment/<cid>/unreport/',
            ],
            'post',
            project_views.comment.unreport_abuse,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/citation/',
                '/project/<pid>/node/<nid>/citation/',
            ],
            'get',
            citation_views.node_citation,
            json_renderer,
        ),

    ], prefix='/api/v1')

    ### Forms ###

    process_rules(app, [
        Rule('/forms/registration/', 'get', website_views.registration_form, json_renderer),
        Rule('/forms/signin/', 'get', website_views.signin_form, json_renderer),
        Rule('/forms/forgot_password/', 'get', website_views.forgot_password_form, json_renderer),
        Rule('/forms/reset_password/', 'get', website_views.reset_password_form, json_renderer),
    ], prefix='/api/v1')

    ### Discovery ###

    process_rules(app, [

        Rule('/explore/activity/', 'get', discovery_views.activity,
             OsfWebRenderer('public/pages/active_nodes.mako')),

    ])

    ### Auth ###

    # Web

    process_rules(app, [

        Rule(
            '/confirm/<uid>/<token>/',
            'get',
            auth_views.confirm_email_get,
            # View will either redirect or display error message
            OsfWebRenderer('error.mako', render_mako_string)
        ),

        Rule(
            '/resend/',
            ['get', 'post'],
            auth_views.resend_confirmation,
            OsfWebRenderer('resend.mako', render_mako_string)
        ),

        Rule(
            '/resetpassword/<verification_key>/',
            ['get', 'post'],
            auth_views.reset_password,
            OsfWebRenderer('public/resetpassword.mako', render_mako_string)
        ),

        # TODO: Remove `auth_register_post`
        Rule('/register/', 'post', auth_views.auth_register_post,
             OsfWebRenderer('public/login.mako')),
        Rule('/api/v1/register/', 'post', auth_views.register_user, json_renderer),

        Rule(['/login/', '/account/'], 'get',
             auth_views.auth_login, OsfWebRenderer('public/login.mako')),
        Rule('/login/', 'post', auth_views.auth_login,
             OsfWebRenderer('public/login.mako'), endpoint_suffix='__post'),
        Rule('/login/first/', 'get', auth_views.auth_login,
             OsfWebRenderer('public/login.mako'),
             endpoint_suffix='__first', view_kwargs={'first': True}),

        Rule('/logout/', 'get', auth_views.auth_logout, notemplate),

        Rule('/forgotpassword/', 'post', auth_views.forgot_password,
             OsfWebRenderer('public/login.mako')),

        Rule([
            '/midas/', '/summit/', '/accountbeta/', '/decline/'
        ], 'get', auth_views.auth_registerbeta, OsfWebRenderer('', render_mako_string)),

        Rule('/login/connected_tools/',
             'get',
             landing_page_views.connected_tools,
             OsfWebRenderer('public/login_landing.mako')),

        Rule('/login/enriched_profile/',
             'get',
             landing_page_views.enriched_profile,
             OsfWebRenderer('public/login_landing.mako')),

    ])

    ### Profile ###

    # Web

    process_rules(app, [
        Rule('/profile/', 'get', profile_views.profile_view, OsfWebRenderer('profile.mako')),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id,
             OsfWebRenderer('profile.mako')),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history,
             OsfWebRenderer('profile/key_history.mako')),
        Rule('/addons/', 'get', profile_views.profile_addons,
             OsfWebRenderer('profile/addons.mako')),
        Rule(["/user/merge/"], 'get', auth_views.merge_user_get,
             OsfWebRenderer("merge_accounts.mako")),
        Rule(["/user/merge/"], 'post', auth_views.merge_user_post,
             OsfWebRenderer("merge_accounts.mako")),
        # Route for claiming and setting email and password.
        # Verification token must be querystring argument
        Rule(['/user/<uid>/<pid>/claim/'], ['get', 'post'],
             project_views.contributor.claim_user_form, OsfWebRenderer('claim_account.mako')),
        Rule(['/user/<uid>/<pid>/claim/verify/<token>/'], ['get', 'post'],
             project_views.contributor.claim_user_registered,
             OsfWebRenderer('claim_account_registered.mako')),


        Rule(
            '/settings/',
            'get',
            profile_views.user_profile,
            OsfWebRenderer('profile/settings.mako'),
        ),

        Rule(
            '/settings/account/',
            'get',
            profile_views.user_account,
            OsfWebRenderer('profile/account.mako'),
        ),

        Rule(
            '/settings/account/password',
            'post',
            profile_views.user_account_password,
            OsfWebRenderer('profile/account.mako'),
        ),

        Rule(
            '/settings/addons/',
            'get',
            profile_views.user_addons,
            OsfWebRenderer('profile/addons.mako'),
        ),

        Rule(
            '/settings/notifications/',
            'get',
            profile_views.user_notifications,
            OsfWebRenderer('profile/notifications.mako'),
        ),

    ])

    # API

    process_rules(app, [

        Rule('/profile/', 'get', profile_views.profile_view, json_renderer),
        Rule('/profile/', 'put', profile_views.update_user, json_renderer),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, json_renderer),

        # Used by profile.html
        Rule('/profile/<uid>/edit/', 'post', profile_views.edit_profile, json_renderer),
        Rule('/profile/<uid>/public_projects/', 'get',
             profile_views.get_public_projects, json_renderer),
        Rule('/profile/<uid>/public_components/', 'get',
             profile_views.get_public_components, json_renderer),

        Rule('/settings/keys/', 'get', profile_views.get_keys, json_renderer),
        Rule('/settings/create_key/', 'post', profile_views.create_user_key, json_renderer),
        Rule('/settings/revoke_key/', 'post', profile_views.revoke_user_key, json_renderer),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, json_renderer),

        Rule('/profile/<user_id>/summary/', 'get',
             profile_views.get_profile_summary, json_renderer),
        Rule('/user/<uid>/<pid>/claim/email/', 'post',
             project_views.contributor.claim_user_post, json_renderer),

        Rule(
            [
                '/profile/gravatar/',
                '/users/gravatar/',
                '/profile/gravatar/<size>',
                '/users/gravatar/<size>',
            ],
            'get',
            profile_views.current_user_gravatar,
            json_renderer,
        ),

        Rule(
            [
                '/profile/<uid>/gravatar/',
                '/users/<uid>/gravatar/',
                '/profile/<uid>/gravatar/<size>',
                '/users/<uid>/gravatar/<size>',
            ],
            'get',
            profile_views.get_gravatar,
            json_renderer,
        ),


        # Rules for user profile configuration
        Rule('/settings/names/', 'get', profile_views.serialize_names, json_renderer),
        Rule('/settings/names/', 'put', profile_views.unserialize_names, json_renderer),
        Rule('/settings/names/impute/', 'get', profile_views.impute_names, json_renderer),

        Rule(
            [
                '/settings/social/',
                '/settings/social/<uid>/',
            ],
            'get',
            profile_views.serialize_social,
            json_renderer,
        ),

        Rule(
            [
                '/settings/jobs/',
                '/settings/jobs/<uid>/',
            ],
            'get',
            profile_views.serialize_jobs,
            json_renderer,
        ),

        Rule(
            [
                '/settings/schools/',
                '/settings/schools/<uid>/',
            ],
            'get',
            profile_views.serialize_schools,
            json_renderer,
        ),

        Rule(
            [
                '/settings/social/',
                '/settings/social/<uid>/',
            ],
            'put',
            profile_views.unserialize_social,
            json_renderer
        ),

        Rule(
            [
                '/settings/jobs/',
                '/settings/jobs/<uid>/',
            ],
            'put',
            profile_views.unserialize_jobs,
            json_renderer
        ),

        Rule(
            [
                '/settings/schools/',
                '/settings/schools/<uid>/',
            ],
            'put',
            profile_views.unserialize_schools,
            json_renderer
        ),

    ], prefix='/api/v1',)

    ### Search ###

    # Web

    process_rules(app, [

        Rule('/search/', 'get', {}, OsfWebRenderer('search.mako')),
        Rule('/share/', 'get', {}, OsfWebRenderer('share_search.mako')),
        Rule('/share_dashboard/', 'get', {}, OsfWebRenderer('share_dashboard.mako')),

        Rule('/api/v1/user/search/', 'get', search_views.search_contributor, json_renderer),

        Rule(
            '/api/v1/search/node/',
            'post',
            project_views.node.search_node,
            json_renderer,
        ),

    ])

    # API

    process_rules(app, [

        Rule(['/search/', '/search/<type>/'], ['get', 'post'], search_views.search_search, json_renderer),
        Rule('/search/projects/', 'get', search_views.search_projects_by_title, json_renderer),
        Rule('/share/', ['get', 'post'], search_views.search_share, json_renderer),
        Rule('/share/stats/', 'get', search_views.search_share_stats, json_renderer),

    ], prefix='/api/v1')

    # Project

    # Web

    process_rules(app, [

        Rule('/', 'get', website_views.index, OsfWebRenderer('index.mako')),
        Rule('/goodbye/', 'get', goodbye, OsfWebRenderer('index.mako')),

        Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', project_views.node.view_project, OsfWebRenderer('project/project.mako')),

        # Create a new subproject/component
        Rule('/project/<pid>/newnode/', 'post', project_views.node.project_new_node,
             OsfWebRenderer('', render_mako_string)),

        Rule([
            '/project/<pid>/key_history/<kid>/',
            '/project/<pid>/node/<nid>/key_history/<kid>/',
        ], 'get', project_views.key.node_key_history, OsfWebRenderer('project/key_history.mako')),

        # # TODO: Add API endpoint for tags
        # Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, OsfWebRenderer('tags.mako')),

        Rule('/folder/<nid>', 'get', project_views.node.folder_new,
             OsfWebRenderer('project/new_folder.mako')),
        Rule('/api/v1/folder/<nid>', 'post', project_views.node.folder_new_post, json_renderer),
        Rule('/project/new/<pid>/beforeTemplate/', 'get',
             project_views.node.project_before_template, json_renderer),

        Rule(
            [
                '/project/<pid>/contributors/',
                '/project/<pid>/node/<nid>/contributors/',
            ],
            'get',
            project_views.node.node_contributors,
            OsfWebRenderer('project/contributors.mako'),
        ),

        Rule(
            [
                '/project/<pid>/settings/',
                '/project/<pid>/node/<nid>/settings/',
            ],
            'get',
            project_views.node.node_setting,
            OsfWebRenderer('project/settings.mako')
        ),

        # Permissions
        Rule(
            [
                '/project/<pid>/permissions/<permissions>/',
                '/project/<pid>/node/<nid>/permissions/<permissions>/',
            ],
            'post',
            project_views.node.project_set_privacy,
            OsfWebRenderer('project/project.mako')
        ),

        ### Logs ###

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, OsfWebRenderer('project/forks.mako')),

        # Registrations
        Rule([
            '/project/<pid>/register/',
            '/project/<pid>/node/<nid>/register/',
        ], 'get', project_views.register.node_register_page,
            OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'get', project_views.register.node_register_template_page,
            OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/registrations/',
            '/project/<pid>/node/<nid>/registrations/',
        ], 'get', project_views.node.node_registrations,
            OsfWebRenderer('project/registrations.mako')),

        # Statistics
        Rule([
            '/project/<pid>/statistics/',
            '/project/<pid>/node/<nid>/statistics/',
        ], 'get', project_views.node.project_statistics,
            OsfWebRenderer('project/statistics.mako')),

        ### Files ###

        # Note: Web endpoint for files view must pass `mode` = `page` to
        # include project view data and JS includes
        Rule(
            [
                '/project/<pid>/files/',
                '/project/<pid>/node/<nid>/files/',
            ],
            'get',
            project_views.file.collect_file_trees,
            OsfWebRenderer('project/files.mako'),
            view_kwargs={'mode': 'page'},
        ),
        Rule(
            [
                '/project/<pid>/files/<provider>/<path:path>/',
                '/project/<pid>/node/<nid>/files/<provider>/<path:path>/',
            ],
            'get',
            addon_views.addon_view_or_download_file,
            OsfWebRenderer('project/view_file.mako')
        ),
        Rule(
            [

                # Legacy Addon view file paths
                '/project/<pid>/<provider>/files/<path:path>/',
                '/project/<pid>/node/<nid>/<provider>/files/<path:path>/',

                '/project/<pid>/<provider>/files/<path:path>/download/',
                '/project/<pid>/node/<nid>/<provider>/files/<path:path>/download/',

                # Legacy routes for `download_file`
                '/project/<pid>/osffiles/<fid>/download/',
                '/project/<pid>/node/<nid>/osffiles/<fid>/download/',

                # Legacy routes for `view_file`
                '/project/<pid>/osffiles/<fid>/',
                '/project/<pid>/node/<nid>/osffiles/<fid>/',

                # Note: Added these old URLs for backwards compatibility with
                # hard-coded links.
                '/project/<pid>/osffiles/download/<fid>/',
                '/project/<pid>/node/<nid>/osffiles/download/<fid>/',
                '/project/<pid>/files/<fid>/',
                '/project/<pid>/node/<nid>/files/<fid>/',
                '/project/<pid>/files/download/<fid>/',
                '/project/<pid>/node/<nid>/files/download/<fid>/',

                # Legacy routes for `download_file_by_version`
                '/project/<pid>/osffiles/<fid>/version/<vid>/download/',
                '/project/<pid>/node/<nid>/osffiles/<fid>/version/<vid>/download/',
                # Note: Added these old URLs for backwards compatibility with
                # hard-coded links.
                '/project/<pid>/osffiles/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/osffiles/<fid>/version/<vid>/',
                '/project/<pid>/osffiles/download/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/osffiles/download/<fid>/version/<vid>/',
                '/project/<pid>/files/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/files/<fid>/version/<vid>/',
                '/project/<pid>/files/download/<fid>/version/<vid>/',
                '/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',

                # api/v1 Legacy routes for `download_file`
                '/api/v1/project/<pid>/osffiles/<fid>/',
                '/api/v1/project/<pid>/node/<nid>/osffiles/<fid>/',
                '/api/v1/project/<pid>/files/download/<fid>/',
                '/api/v1/project/<pid>/node/<nid>/files/download/<fid>/',

                #api/v1 Legacy routes for `download_file_by_version`
                '/api/v1/project/<pid>/osffiles/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/node/<nid>/osffiles/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/files/download/<fid>/version/<vid>/',
                '/api/v1/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',
            ],
            'get',
            addon_views.addon_view_or_download_file_legacy,
            json_renderer
        ),



    ])

    # API

    process_rules(app, [

        Rule(
            '/email/meeting/',
            'post',
            conference_views.meeting_hook,
            json_renderer,
        ),
        Rule('/mailchimp/hooks/', 'get', profile_views.mailchimp_get_endpoint, json_renderer),

        Rule('/mailchimp/hooks/', 'post', profile_views.sync_data_from_mailchimp, json_renderer),

        # Create project, used by projectCreator.js
        Rule('/project/new/', 'post', project_views.node.project_new_post, json_renderer),

        Rule([
            '/project/<pid>/contributors_abbrev/',
            '/project/<pid>/node/<nid>/contributors_abbrev/',
        ], 'get', project_views.contributor.get_node_contributors_abbrev, json_renderer),

        Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, json_renderer),

        Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', project_views.node.view_project, json_renderer),
        Rule([
            '/project/<pid>/expand/',
            '/project/<pid>/node/<nid>/expand/',
        ], 'post', project_views.node.expand, json_renderer),
        Rule([
            '/project/<pid>/collapse/',
            '/project/<pid>/node/<nid>/collapse/',
        ], 'post', project_views.node.collapse, json_renderer),

        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>/pointer/',
            ],
            'get',
            project_views.node.get_pointed,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>/pointer/',
            ],
            'post',
            project_views.node.add_pointers,
            json_renderer,
        ),
        Rule(
            [
                '/pointer/',
            ],
            'post',
            project_views.node.add_pointer,
            json_renderer,
        ),
        Rule(
            [
                '/pointers/move/',
            ],
            'post',
            project_views.node.move_pointers,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>pointer/',
            ],
            'delete',
            project_views.node.remove_pointer,
            json_renderer,
        ),
        Rule(
            [
                '/folder/<pid>/pointer/<pointer_id>',
            ],
            'delete',
            project_views.node.remove_pointer_from_folder,
            json_renderer,
        ),
        Rule(
            [
                '/folder/<pid>/pointers/',
            ],
            'delete',
            project_views.node.remove_pointers_from_folder,
            json_renderer,
        ),
        Rule(
            [
                '/folder/<pid>',
            ],
            'delete',
            project_views.node.delete_folder,
            json_renderer,
        ),
        Rule('/folder/', 'put', project_views.node.add_folder, json_renderer),
        Rule([
            '/project/<pid>/get_summary/',
            '/project/<pid>/node/<nid>/get_summary/',
        ], 'get', project_views.node.get_summary, json_renderer),

        Rule([
            '/project/<pid>/get_children/',
            '/project/<pid>/node/<nid>/get_children/',
        ], 'get', project_views.node.get_children, json_renderer),
        Rule([
            '/project/<pid>/get_folder_pointers/'
        ], 'get', project_views.node.get_folder_pointers, json_renderer),
        Rule([
            '/project/<pid>/get_forks/',
            '/project/<pid>/node/<nid>/get_forks/',
        ], 'get', project_views.node.get_forks, json_renderer),
        Rule([
            '/project/<pid>/get_registrations/',
            '/project/<pid>/node/<nid>/get_registrations/',
        ], 'get', project_views.node.get_registrations, json_renderer),

        Rule('/log/<log_id>/', 'get', project_views.log.get_log, json_renderer),

        Rule([
            '/project/<pid>/log/',
            '/project/<pid>/node/<nid>/log/',
        ], 'get', project_views.log.get_logs, json_renderer),

        Rule([
            '/project/<pid>/get_contributors/',
            '/project/<pid>/node/<nid>/get_contributors/',
        ], 'get', project_views.contributor.get_contributors, json_renderer),

        Rule([
            '/project/<pid>/get_contributors_from_parent/',
            '/project/<pid>/node/<nid>/get_contributors_from_parent/',
        ], 'get', project_views.contributor.get_contributors_from_parent, json_renderer),

        # Reorder contributors
        Rule(
            [
                '/project/<pid>/contributors/manage/',
                '/project/<pid>/node/<nid>/contributors/manage/',
            ],
            'POST',
            project_views.contributor.project_manage_contributors,
            json_renderer,
        ),

        Rule([
            '/project/<pid>/get_most_in_common_contributors/',
            '/project/<pid>/node/<nid>/get_most_in_common_contributors/',
        ], 'get', project_views.contributor.get_most_in_common_contributors, json_renderer),

        Rule([
            '/project/<pid>/get_recently_added_contributors/',
            '/project/<pid>/node/<nid>/get_recently_added_contributors/',
        ], 'get', project_views.contributor.get_recently_added_contributors, json_renderer),

        Rule([
            '/project/<pid>/get_editable_children/',
            '/project/<pid>/node/<nid>/get_editable_children/',
        ], 'get', project_views.node.get_editable_children, json_renderer),


        # Private Link
        Rule([
            '/project/<pid>/private_link/',
            '/project/<pid>/node/<nid>/private_link/',
        ], 'post', project_views.node.project_generate_private_link_post, json_renderer),

        Rule([
            '/project/<pid>/private_link/edit/',
            '/project/<pid>/node/<nid>/private_link/edit/',
        ], 'put', project_views.node.project_private_link_edit, json_renderer),

        Rule([
            '/project/<pid>/private_link/',
            '/project/<pid>/node/<nid>/private_link/',
        ], 'delete', project_views.node.remove_private_link, json_renderer),

        Rule([
            '/project/<pid>/private_link/',
            '/project/<pid>/node/<nid>/private_link/',
        ], 'get', project_views.node.private_link_table, json_renderer),

        # Create, using existing project as a template
        Rule([
            '/project/new/<nid>/',
        ], 'post', project_views.node.project_new_from_template, json_renderer),

        # Remove
        Rule(
            [
                '/project/<pid>/',
                '/project/<pid>/node/<nid>/',
            ],
            'delete',
            project_views.node.component_remove,
            json_renderer,
        ),

        # API keys
        Rule([
            '/project/<pid>/create_key/',
            '/project/<pid>/node/<nid>/create_key/',
        ], 'post', project_views.key.create_node_key, json_renderer),
        Rule([
            '/project/<pid>/revoke_key/',
            '/project/<pid>/node/<nid>/revoke_key/'
        ], 'post', project_views.key.revoke_node_key, json_renderer),
        Rule([
            '/project/<pid>/keys/',
            '/project/<pid>/node/<nid>/keys/',
        ], 'get', project_views.key.get_node_keys, json_renderer),

        # Reorder components
        Rule('/project/<pid>/reorder_components/', 'post',
             project_views.node.project_reorder_components, json_renderer),

        # Edit node
        Rule([
            '/project/<pid>/edit/',
            '/project/<pid>/node/<nid>/edit/',
        ], 'post', project_views.node.edit_node, json_renderer),

        # Tags
        Rule([
            '/project/<pid>/addtag/<tag>/',
            '/project/<pid>/node/<nid>/addtag/<tag>/',
        ], 'post', project_views.tag.project_addtag, json_renderer),
        Rule([
            '/project/<pid>/removetag/<tag>/',
            '/project/<pid>/node/<nid>/removetag/<tag>/',
        ], 'post', project_views.tag.project_removetag, json_renderer),

        # Add / remove contributors
        Rule([
            '/project/<pid>/contributors/',
            '/project/<pid>/node/<nid>/contributors/',
        ], 'post', project_views.contributor.project_contributors_post, json_renderer),
        Rule([
            '/project/<pid>/beforeremovecontributors/',
            '/project/<pid>/node/<nid>/beforeremovecontributors/',
        ], 'post', project_views.contributor.project_before_remove_contributor, json_renderer),
        # TODO(sloria): should be a delete request to /contributors/
        Rule([
            '/project/<pid>/removecontributors/',
            '/project/<pid>/node/<nid>/removecontributors/',
        ], 'post', project_views.contributor.project_removecontributor, json_renderer),

        # Forks
        Rule(
            [
                '/project/<pid>/fork/before/',
                '/project/<pid>/node/<nid>/fork/before/',
            ], 'get', project_views.node.project_before_fork, json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/fork/',
                '/project/<pid>/node/<nid>/fork/',
            ], 'post', project_views.node.node_fork_page, json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/fork/',
                '/project/<pid>/node/<nid>/pointer/fork/',
            ], 'post', project_views.node.fork_pointer, json_renderer,
        ),

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, json_renderer),

        # Registrations
        Rule([
            '/project/<pid>/beforeregister/',
            '/project/<pid>/node/<nid>/beforeregister',
        ], 'get', project_views.register.project_before_register, json_renderer),
        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'get', project_views.register.node_register_template_page, json_renderer),

        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'post', project_views.register.node_register_template_page_post, json_renderer),

        # Statistics
        Rule([
            '/project/<pid>/statistics/',
            '/project/<pid>/node/<nid>/statistics/',
        ], 'get', project_views.node.project_statistics, json_renderer),

        # Permissions
        Rule([
            '/project/<pid>/permissions/<permissions>/',
            '/project/<pid>/node/<nid>/permissions/<permissions>/',
        ], 'post', project_views.node.project_set_privacy, json_renderer),

        Rule([
            '/project/<pid>/permissions/beforepublic/',
            '/project/<pid>/node/<nid>/permissions/beforepublic/',
        ], 'get', project_views.node.project_before_set_public, json_renderer),

        ### Wiki ###

        ### Watching ###
        Rule([
            '/project/<pid>/watch/',
            '/project/<pid>/node/<nid>/watch/'
        ], 'post', project_views.node.watch_post, json_renderer),

        Rule([
            '/project/<pid>/unwatch/',
            '/project/<pid>/node/<nid>/unwatch/'
        ], 'post', project_views.node.unwatch_post, json_renderer),

        Rule([
            '/project/<pid>/togglewatch/',
            '/project/<pid>/node/<nid>/togglewatch/'
        ], 'post', project_views.node.togglewatch_post, json_renderer),

        Rule([
            '/watched/logs/'
        ], 'get', website_views.watched_logs_get, json_renderer),
        ### Accounts ###
        Rule([
            '/user/merge/'
        ], 'post', auth_views.merge_user_post, json_renderer),

        # Combined files
        Rule(
            [
                '/project/<pid>/files/',
                '/project/<pid>/node/<nid>/files/'
            ],
            'get',
            project_views.file.collect_file_trees,
            json_renderer,
        ),

        # Endpoint to fetch Rubeus.JS/Hgrid-formatted data
        Rule(
            [
                '/project/<pid>/files/grid/',
                '/project/<pid>/node/<nid>/files/grid/'
            ],
            'get',
            project_views.file.grid_data,
            json_renderer
        ),

        # Settings

        Rule(
            '/files/auth/',
            'get',
            addon_views.get_auth,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/waterbutler/logs/',
                '/project/<pid>/node/<nid>/waterbutler/logs/',
            ],
            'put',
            addon_views.create_waterbutler_log,
            json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/files/<provider>/<path:path>/',
                '/project/<pid>/node/<nid>/files/<provider>/<path:path>/',
            ],
            'get',
            addon_views.addon_render_file,
            json_renderer
        ),
        Rule(
            '/settings/addons/',
            'post',
            profile_views.user_choose_addons,
            json_renderer,
        ),

        Rule(
            '/settings/notifications/',
            'get',
            profile_views.user_notifications,
            json_renderer,
        ),

        Rule(
            '/settings/notifications/',
            'post',
            profile_views.user_choose_mailing_lists,
            json_renderer,
        ),

        Rule(
            '/subscriptions/',
            'get',
            notification_views.get_subscriptions,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/subscriptions/',
                '/project/<pid>/node/<nid>/subscriptions/'
            ],
            'get',
            notification_views.get_node_subscriptions,
            json_renderer,
        ),

        Rule(
            '/subscriptions/',
            'post',
            notification_views.configure_subscription,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/settings/addons/',
                '/project/<pid>/node/<nid>/settings/addons/',
            ],
            'post',
            project_views.node.node_choose_addons,
            json_renderer,
        ),

        Rule(
            [
                '/project/<pid>/settings/comments/',
                '/project/<pid>/node/<nid>/settings/comments/',
            ],
            'post',
            project_views.node.configure_comments,
            json_renderer,
        ),

        # Invite Users
        Rule(
            [
                '/project/<pid>/invite_contributor/',
                '/project/<pid>/node/<nid>/invite_contributor/'
            ],
            'post',
            project_views.contributor.invite_contributor_post,
            json_renderer
        ),
    ], prefix='/api/v1')

    # Set up static routing for addons
    # NOTE: We use nginx to serve static addon assets in production
    addon_base_path = os.path.abspath('website/addons')
    if settings.DEV_MODE:
        @app.route('/static/addons/<addon>/<path:filename>')
        def addon_static(addon, filename):
            addon_path = os.path.join(addon_base_path, addon, 'static')
            return send_from_directory(addon_path, filename)
