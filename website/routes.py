# -*- coding: utf-8 -*-
import httplib as http

import framework
from framework.exceptions import HTTPError
from framework import (Rule, process_rules,
                       WebRenderer, json_renderer,
                       render_mako_string)
from framework.auth import views as auth_views

from website import settings
from website import views as website_routes
from website.search import views as search_views
from website.discovery import views as discovery_views
from website.profile import views as profile_views
from website.project import views as project_views
from website.assets import env as assets_env


def get_globals():
    user = framework.auth.get_current_user()
    return {
        'user_name': user.username if user else '',
        'user_full_name': user.fullname if user else '',
        'user_id': user._primary_key if user else '',
        'user_url': user.url if user else '',
        'user_api_url': user.api_url if user else '',
        'display_name': framework.auth.get_display_name(user.username) if user else '',
        'use_cdn': settings.USE_CDN_FOR_CLIENT_LIBS,
        'dev_mode': settings.DEV_MODE,
        'allow_login': settings.ALLOW_LOGIN,
        'status': framework.status.pop_status_messages(),
        'js_all': assets_env['js'].urls(),
        'css_all': assets_env['css'].urls()
    }


class OsfWebRenderer(WebRenderer):

    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)


def favicon():
    return framework.send_from_directory(
        settings.STATIC_FOLDER,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )


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
        Rule([
            '/<guid>/',
            '/<guid>/<path:suffix>',
        ], ['get', 'post'], website_routes.resolve_guid, OsfWebRenderer('', render_mako_string)),
    ])

    process_rules(app, [
        Rule('/favicon.ico', 'get', favicon, json_renderer),
    ])

    ### Base ###

    process_rules(app, [

        Rule('/dashboard/', 'get', website_routes.dashboard, OsfWebRenderer('dashboard.mako')),
        Rule('/reproducibility/', 'get', website_routes.reproducibility, OsfWebRenderer('', render_mako_string)),

        Rule('/about/', 'get', {}, OsfWebRenderer('public/pages/about.mako')),
        Rule('/howosfworks/', 'get', {}, OsfWebRenderer('public/pages/howosfworks.mako')),
        Rule('/faq/', 'get', {}, OsfWebRenderer('public/pages/faq.mako')),
        Rule('/getting-started/', 'get', {}, OsfWebRenderer('public/pages/getting_started.mako')),
        Rule('/explore/', 'get', {}, OsfWebRenderer('public/explore.mako')),
        Rule(['/messages/', '/help/'], 'get', {}, OsfWebRenderer('public/comingsoon.mako')),

    ])

    process_rules(app, [

        Rule('/dashboard/get_nodes/', 'get', website_routes.get_dashboard_nodes, json_renderer),

    ], prefix='/api/v1')

    ### Meta-data ###

    process_rules(app, [

        Rule([
            '/metadata/node/comment/',
            '/metadata/comment/comment/',
        ], 'get', website_routes.node_comment_schema, json_renderer),

        # Get comments
        Rule('/guid/<guid>/comments/', 'get', website_routes.get_comments_guid, json_renderer),

        # Add comment
        Rule('/guid/<guid>/comment/', 'post', website_routes.add_comment_guid, json_renderer),

    ], prefix='/api/v1')

    ### Forms ###

    process_rules(app, [

        Rule('/forms/registration/', 'get', website_routes.registration_form, json_renderer),
        Rule('/forms/signin/', 'get', website_routes.signin_form, json_renderer),
        Rule('/forms/forgot_password/', 'get', website_routes.forgot_password_form, json_renderer),
        Rule('/forms/reset_password/', 'get', website_routes.reset_password_form, json_renderer),
        Rule('/forms/new_project/', 'get', website_routes.new_project_form, json_renderer)

    ], prefix='/api/v1')

    ### Discovery ###

    process_rules(app, [

        Rule('/explore/activity/', 'get', discovery_views.activity, OsfWebRenderer('public/pages/active_nodes.mako')),

    ])

    ### Auth ###

    # Web

    process_rules(app, [

        Rule(
            '/resetpassword/<verification_key>/',
            ['get', 'post'],
            auth_views.reset_password,
            OsfWebRenderer('public/resetpassword.mako', render_mako_string)
        ),

        Rule('/register/', 'post', auth_views.auth_register_post, OsfWebRenderer('public/login.mako')),

        Rule(['/login/', '/account/'], 'get', auth_views.auth_login, OsfWebRenderer('public/login.mako')),
        Rule('/login/', 'post', auth_views.auth_login, OsfWebRenderer('public/login.mako'), endpoint_suffix='__post'),

        Rule('/logout/', 'get', auth_views.auth_logout, OsfWebRenderer('', render_mako_string)),

        Rule('/forgotpassword/', 'post', auth_views.forgot_password, OsfWebRenderer('public/login.mako')),

        Rule([
            '/midas/', '/summit/', '/accountbeta/', '/decline/'
        ], 'get', auth_views.auth_registerbeta, OsfWebRenderer('', render_mako_string)),

    ])

    ### Profile ###

    # Web

    process_rules(app, [

        Rule('/profile/', 'get', profile_views.profile_view, OsfWebRenderer('profile.mako')),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, OsfWebRenderer('profile.mako')),
        Rule('/settings/', 'get', profile_views.profile_settings, OsfWebRenderer('settings.mako')),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, OsfWebRenderer('profile/key_history.mako')),
        Rule('/addons/', 'get', profile_views.profile_addons, OsfWebRenderer('profile/addons.mako')),
        Rule(["/user/merge/"], 'get', auth_views.merge_user_get, OsfWebRenderer("merge_accounts.mako")),
        Rule(["/user/merge/"], 'post', auth_views.merge_user_post, OsfWebRenderer("merge_accounts.mako"))

    ])

    # API

    process_rules(app, [

        Rule('/profile/', 'get', profile_views.profile_view, json_renderer),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, json_renderer),

        # Used by profile.html
        Rule('/profile/<uid>/edit/', 'post', profile_views.edit_profile, json_renderer),
        Rule('/profile/<uid>/public_projects/', 'get', profile_views.get_public_projects, json_renderer),
        Rule('/profile/<uid>/public_components/', 'get', profile_views.get_public_components, json_renderer),

        Rule('/settings/', 'get', profile_views.profile_settings, json_renderer),
        Rule('/settings/keys/', 'get', profile_views.get_keys, json_renderer),
        Rule('/settings/create_key/', 'post', profile_views.create_user_key, json_renderer),
        Rule('/settings/revoke_key/', 'post', profile_views.revoke_user_key, json_renderer),
        Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, json_renderer),

        Rule('/settings/names/parse/', 'post', profile_views.parse_names, json_renderer),
        Rule('/settings/names/', 'post', profile_views.post_names, json_renderer),

        Rule('/profile/<user_id>/summary/', 'get', profile_views.get_profile_summary, json_renderer),

    ], prefix='/api/v1',)

    ### Search ###

    # Web

    process_rules(app, [

        Rule('/search/', 'get', search_views.search_search, OsfWebRenderer('search.mako')),

        Rule('/api/v1/user/search/', 'get', search_views.search_contributor, json_renderer),

    ])

    # API

    process_rules(app, [

        Rule('/search/', 'get', search_views.search_search, json_renderer),

    ], prefix='/api/v1')

    # Project

    # Web

    process_rules(app, [

        Rule('/', 'get', {}, OsfWebRenderer('index.mako')),

        Rule([
            '/project/<pid>/',
            '/project/<pid>/node/<nid>/',
        ], 'get', project_views.node.view_project, OsfWebRenderer('project.mako')),

        Rule([
            '/project/<pid>/key_history/<kid>/',
            '/project/<pid>/node/<nid>/key_history/<kid>/',
        ], 'get', project_views.key.node_key_history, OsfWebRenderer('project/key_history.mako')),

        Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, OsfWebRenderer('tags.mako')),

        Rule('/project/new/', 'get', project_views.node.project_new, OsfWebRenderer('project/new.mako')),
        Rule('/project/new/', 'post', project_views.node.project_new_post, OsfWebRenderer('project/new.mako')),

        Rule('/project/<pid>/newnode/', 'post', project_views.node.project_new_node, OsfWebRenderer('project.mako')),

        Rule([
            '/project/<pid>/settings/',
            '/project/<pid>/node/<nid>/settings/',
        ], 'get', project_views.node.node_setting, OsfWebRenderer('project/settings.mako')),

        # Remove
        Rule([
            '/project/<pid>/remove/',
            '/project/<pid>/node/<nid>/remove/',
        ], 'get', project_views.node.component_remove, WebRenderer('', render_mako_string)),

        # Permissions
        Rule([
            '/project/<pid>/permissions/<permissions>/',
            '/project/<pid>/node/<nid>/permissions/<permissions>/',
        ], 'post', project_views.node.project_set_permissions, OsfWebRenderer('project.mako')),

        ### Logs ###

        Rule('/log/<log_id>/', 'get', project_views.log.get_log, OsfWebRenderer('util/render_log.mako')),
        Rule([
            '/project/<pid>/log/',
            '/project/<pid>/node/<nid>/log/',
        ], 'get', project_views.log.get_logs, OsfWebRenderer('util/render_logs.mako')),


        ### Files ###

        Rule([
            '/project/<pid>/files/',
            '/project/<pid>/node/<nid>/files/',
        ], 'get', project_views.file.get_files, OsfWebRenderer('project/files.mako')),

        Rule([
            '/project/<pid>/files/<fid>/',
            '/project/<pid>/node/<nid>/files/<fid>/',
        ], 'get', project_views.file.view_file, OsfWebRenderer('project/file.mako')),

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, OsfWebRenderer('project/forks.mako')),

        # Registrations
        Rule([
            '/project/<pid>/register/',
            '/project/<pid>/node/<nid>/register/',
        ], 'get', project_views.register.node_register_page, OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/register/<template>/',
            '/project/<pid>/node/<nid>/register/<template>/',
        ], 'get', project_views.register.node_register_template_page, OsfWebRenderer('project/register.mako')),

        Rule([
            '/project/<pid>/registrations/',
            '/project/<pid>/node/<nid>/registrations/',
        ], 'get', project_views.node.node_registrations, OsfWebRenderer('project/registrations.mako')),

        # Statistics
        Rule([
            '/project/<pid>/statistics/',
            '/project/<pid>/node/<nid>/statistics/',
        ], 'get', project_views.node.project_statistics, OsfWebRenderer('project/statistics.mako')),

        ### Wiki ###
        Rule([
            '/project/<pid>/wiki/',
            '/project/<pid>/node/<nid>/wiki/',
        ], 'get', project_views.wiki.project_wiki_home, OsfWebRenderer('project/wiki.mako')),

        # View
        Rule([
            '/project/<pid>/wiki/<wid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/',
        ], 'get', project_views.wiki.project_wiki_page, OsfWebRenderer('project/wiki.mako')),

        # Edit | GET
        Rule([
            '/project/<pid>/wiki/<wid>/edit/',
            '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
        ], 'get', project_views.wiki.project_wiki_edit, OsfWebRenderer('project/wiki/edit.mako')),

        # Edit | POST
        Rule([
            '/project/<pid>/wiki/<wid>/edit/',
            '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
        ], 'post', project_views.wiki.project_wiki_edit_post, OsfWebRenderer('project/wiki/edit.mako')),

        # Compare
        Rule([
            '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
        ], 'get', project_views.wiki.project_wiki_compare, OsfWebRenderer('project/wiki/compare.mako')),

        # Versions
        Rule([
            '/project/<pid>/wiki/<wid>/version/<vid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
        ], 'get', project_views.wiki.project_wiki_version, OsfWebRenderer('project/wiki/compare.mako')),

    ])

    # API

    process_rules(app, [

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
            '/project/<pid>/get_summary/',
            '/project/<pid>/node/<nid>/get_summary/',
        ], 'get', project_views.node.get_summary, json_renderer),

        Rule([
            '/project/<pid>/get_children/',
            '/project/<pid>/node/<nid>/get_children/',
        ], 'get', project_views.node.get_children, json_renderer),
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

        Rule([
            '/project/<pid>/get_editable_children/',
            '/project/<pid>/node/<nid>/get_editable_children/',
        ], 'get', project_views.node.get_editable_children, json_renderer),

        # Create
        Rule([
            '/project/new/',
            '/project/<pid>/newnode/',
        ], 'post', project_views.node.project_new_node, json_renderer),

        # Remove
        Rule([
            '/project/<pid>/remove/',
            '/project/<pid>/node/<nid>/remove/',
        ], 'post', project_views.node.component_remove, json_renderer),

        # API keys
        Rule([
            '/project/<pid>/create_key/',
            '/project/<pid>/node/<nid>/create_key/',
        ], 'post', project_views.key.create_node_key, json_renderer),
        Rule([
            '/project/<pid>/revoke_key/',
            '/project/<pid>/node/<nid>/revoke_key/'
        ], 'post', project_views.key.revoke_node_key,  json_renderer),
        Rule([
            '/project/<pid>/keys/',
            '/project/<pid>/node/<nid>/keys/',
        ], 'get', project_views.key.get_node_keys, json_renderer),

        # Reorder components
        Rule('/project/<pid>/reorder_components/', 'post', project_views.node.project_reorder_components, json_renderer),

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

        ### Files ###
        Rule([
            '/project/<pid>/files/',
            '/project/<pid>/node/<nid>/files/',
        ], 'get', project_views.file.list_files, json_renderer),

        Rule([
            '/project/<pid>/file_paths/',
            '/project/<pid>/node/<nid>/file_paths/',
        ], 'get', project_views.file.list_file_paths, json_renderer),

        Rule([
            '/project/<pid>/get_files/',
            '/project/<pid>/node/<nid>/get_files/',
        ], 'get', project_views.file.get_files, json_renderer),

        # Download file
        Rule([
            '/project/<pid>/files/download/<fid>/',
            '/project/<pid>/node/<nid>/files/download/<fid>/',
        ], 'get', project_views.file.download_file, json_renderer),

        # Download file by version
        Rule([
            '/project/<pid>/files/download/<fid>/version/<vid>/',
            '/project/<pid>/node/<nid>/files/download/<fid>/version/<vid>/',
        ], 'get', project_views.file.download_file_by_version, json_renderer),

        Rule([
            '/project/<pid>/files/upload/',
            '/project/<pid>/node/<nid>/files/upload/',
        ], 'get', project_views.file.upload_file_get, json_renderer),
        Rule([
            '/project/<pid>/files/upload/',
            '/project/<pid>/node/<nid>/files/upload/',
        ], 'post', project_views.file.upload_file_public, json_renderer),
        Rule([
            '/project/<pid>/files/delete/<fid>/',
            '/project/<pid>/node/<nid>/files/delete/<fid>/',
        ], 'post', project_views.file.delete_file, json_renderer),

        # Add / remove contributors
        Rule([
            '/project/<pid>/addcontributors/',
            '/project/<pid>/node/<nid>/addcontributors/',
        ], 'post', project_views.contributor.project_addcontributors_post, json_renderer),
        Rule([
            '/project/<pid>/removecontributors/',
            '/project/<pid>/node/<nid>/removecontributors/',
        ], 'post', project_views.contributor.project_removecontributor, json_renderer),

        # Forks
        Rule([
            '/project/<pid>/fork/',
            '/project/<pid>/node/<nid>/fork/',
        ], 'post', project_views.node.node_fork_page, json_renderer),

        # View forks
        Rule([
            '/project/<pid>/forks/',
            '/project/<pid>/node/<nid>/forks/',
        ], 'get', project_views.node.node_forks, json_renderer),

        # Registrations
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
        ], 'post', project_views.node.project_set_permissions, json_renderer),


        ### Wiki ###

        # View
        Rule([
            '/project/<pid>/wiki/<wid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/',
        ], 'get', project_views.wiki.project_wiki_page, json_renderer),

        # Edit | POST
        Rule([
            '/project/<pid>/wiki/<wid>/edit/',
            '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
        ], 'post', project_views.wiki.project_wiki_edit_post, json_renderer),

        # Compare
        Rule([
            '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
        ], 'get', project_views.wiki.project_wiki_compare, json_renderer),

        # Versions
        Rule([
            '/project/<pid>/wiki/<wid>/version/<vid>/',
            '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
        ], 'get', project_views.wiki.project_wiki_version, json_renderer),

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
        ], 'get', website_routes.watched_logs_get, json_renderer),
        ### Accounts ###
        Rule([
            '/user/merge/'
        ], 'post', auth_views.merge_user_post, json_renderer),

    ], prefix='/api/v1')
