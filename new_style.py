from framework.flask import app
import framework
from website import settings
from framework import get_current_user

from framework import (Rule, process_rules,
                       WebRenderer, json_renderer,
                       render_mako_string)


def get_globals():
    user = get_current_user()
    return {
        'user_name' : user.username if user else '',
        'user_full_name' : user.fullname if user else '',
        'user_id' : user._primary_key if user else '',
        'display_name' : get_display_name(user.username) if user else '',
        'use_cdn' : settings.use_cdn_for_client_libs,
        'dev_mode' : settings.dev_mode,
        'allow_login' : settings.allow_login,
        'status' : framework.status.pop_status_messages(),
    }

class OsfWebRenderer(WebRenderer):

    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)


# todo move
def get_display_name(username):
    if username:
        if len(username) > 22:
            return '%s...%s' % (username[:9],username[-10:])
        return username

def view_index():

    display_name = username = framework.get_current_username()
    if username and len(username) > 22:
        display_name = get_display_name(username)

    return {
        'user_name': username,
        'display_name': display_name,
        'status': framework.status.pop_status_messages(),
    }


from framework.auth import views as auth_views
from website import views as website_routes
from website.search import views as search_views
from website.discovery import views as discovery_views
from website.profile import views as profile_views
from website.project import views as project_views


def favicon():
    return framework.send_from_directory(
        settings.static_path,
        'favicon.ico',
        mimetype='image/vnd.microsoft.icon'
    )

process_rules(app, [
    Rule('/favicon.ico', 'get', favicon, json_renderer),
])

### Base ###

process_rules(app, [

    Rule('/dashboard/', 'get', website_routes.dashboard, OsfWebRenderer('dashboard.html', render_mako_string)),
    Rule('/reproducibility/', 'get', website_routes.reproducibility, OsfWebRenderer('', render_mako_string)),

    Rule('/about/', 'get', None, OsfWebRenderer('public/pages/about.mako', render_mako_string)),
    Rule('/howosfworks/', 'get', None, OsfWebRenderer('public/pages/howosfworks.mako', render_mako_string)),
    Rule('/faq/', 'get', None, OsfWebRenderer('public/pages/faq.mako', render_mako_string)),
    Rule('/getting-started/', 'get', None, OsfWebRenderer('public/pages/getting_started.mako', render_mako_string)),
    Rule('/explore/', 'get', None, OsfWebRenderer('public/explore.mako', render_mako_string)),
    Rule(['/messages/', '/help/'], 'get', None, OsfWebRenderer('public/comingsoon.mako', render_mako_string)),

])

process_rules(app, [

    Rule('/dashboard/get_nodes/', 'get', website_routes.get_dashboard_nodes, json_renderer),

], prefix='/api/v1')

### Forms ###

process_rules(app, [

    Rule('/forms/registration/', 'get', website_routes.registration_form, json_renderer),
    Rule('/forms/signin/', 'get', website_routes.signin_form, json_renderer),
    Rule('/forms/forgot_password/', 'get', website_routes.forgot_password_form, json_renderer),
    Rule('/forms/reset_password/', 'get', website_routes.reset_password_form, json_renderer),

], prefix='/api/v1')

### Discovery ###

process_rules(app, [

    Rule('/explore/activity/', 'get', discovery_views.activity, OsfWebRenderer('public/pages/active_nodes.mako', render_mako_string)),

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

    Rule('/register/', 'post', auth_views.auth_register_post, OsfWebRenderer('public/login.mako', render_mako_string)),

    Rule(['/login/', '/account/'], 'get', auth_views.auth_login, OsfWebRenderer('public/login.mako', render_mako_string)),
    Rule('/login/', 'post', auth_views.auth_login, OsfWebRenderer('public/login.mako', render_mako_string), endpoint_suffix='__post'),

    Rule('/logout/', 'get', auth_views.auth_logout, OsfWebRenderer('', None)),

    Rule('/forgotpassword/', 'post', auth_views.forgot_password, OsfWebRenderer('public/login.mako', render_mako_string)),

    Rule([
        '/midas/', '/summit/', '/accountbeta/', '/decline/'
    ], 'get', auth_views.auth_registerbeta, OsfWebRenderer('', render_mako_string)),

])

### Profile ###

# Web

process_rules(app, [

    Rule('/profile/', 'get', profile_views.profile_view, OsfWebRenderer('profile.html', render_mako_string)),
    Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, OsfWebRenderer('profile.html', render_mako_string)),
    Rule('/settings/', 'get', profile_views.profile_settings, OsfWebRenderer('settings.html', render_mako_string)),
    Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, OsfWebRenderer('profile/key_history.html', render_mako_string)),
    Rule('/profile/<uid>/edit', 'post', profile_views.edit_profile, json_renderer),
    Rule('/addons/', 'get', profile_views.profile_addons, OsfWebRenderer('profile/addons.html', render_mako_string)),

])

# API

process_rules(app, [

    Rule('/profile/', 'get', profile_views.profile_view, json_renderer),
    Rule('/profile/<uid>/', 'get', profile_views.profile_view_id, json_renderer),

    # Used by profile.html
    Rule('/profile/<uid>/public_projects/', 'get', profile_views.get_public_projects, json_renderer),
    Rule('/profile/<uid>/public_components/', 'get', profile_views.get_public_components, json_renderer),

    Rule('/settings/', 'get', profile_views.profile_settings, json_renderer),
    Rule('/settings/keys/', 'get', profile_views.get_keys, json_renderer),
    Rule('/settings/create_key/', 'post', profile_views.create_user_key, json_renderer),
    Rule('/settings/revoke_key/', 'post', profile_views.revoke_user_key, json_renderer),
    Rule('/settings/key_history/<kid>/', 'get', profile_views.user_key_history, json_renderer),

    Rule('/profile/<user_id>/summary/', 'get', profile_views.get_profile_summary, json_renderer),

], prefix='/api/v1',)

### Search ###

# Web

process_rules(app, [

    Rule('/search/', 'get', search_views.search_search, OsfWebRenderer('search.mako', render_mako_string)),

])

# API

process_rules(app, [

    Rule('/search/', 'get', search_views.search_search, json_renderer),

], prefix='/api/v1')

# Project

# Web

process_rules(app, [

    Rule('/', 'get', view_index, OsfWebRenderer('index.html', render_mako_string)),

    Rule([
        '/project/<pid>/',
        '/project/<pid>/node/<nid>/',
    ], 'get', project_views.node.view_project, OsfWebRenderer('project.html', render_mako_string)),

    Rule([
        '/project/<pid>/key_history/<kid>/',
        '/project/<pid>/node/<nid>/key_history/<kid>/',
    ], 'get', project_views.key.node_key_history, OsfWebRenderer('project/key_history.html', render_mako_string)),

    Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, OsfWebRenderer('tags.html', render_mako_string)),

    Rule('/project/new/', 'get', project_views.node.project_new, OsfWebRenderer('project/new.html', render_mako_string)),
    Rule('/project/new/', 'post', project_views.node.project_new_post, OsfWebRenderer('project/new.html', render_mako_string)),

    Rule('/project/<pid>/newnode/', 'post', project_views.node.project_new_node, OsfWebRenderer('project.html', render_mako_string)),

    Rule([
        '/project/<pid>/settings/',
        '/project/<pid>/node/<nid>/settings/',
    ], 'get', project_views.node.node_setting, OsfWebRenderer('project/settings.html', render_mako_string)),

    # Remove
    Rule([
        '/project/<pid>/remove/',
        '/project/<pid>/node/<nid>/remove/',
    ], 'get', project_views.node.component_remove, WebRenderer(None, None)),

    # Permissions
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/permissions/<permissions>/',
        '/project/<pid>/node/<nid>/permissions/<permissions>/',
    ], 'get', project_views.node.project_set_permissions, OsfWebRenderer('project.html', render_mako_string)),

    ### Logs ###

    Rule('/log/<log_id>/', 'get', project_views.log.get_log, OsfWebRenderer('util/render_log.html', render_mako_string)),
    Rule([
        '/project/<pid>/log/',
        '/project/<pid>/node/<nid>/log/',
    ], 'get', project_views.log.get_logs, OsfWebRenderer('util/render_logs.html', render_mako_string)),


    ### Files ###

    Rule([
        '/project/<pid>/files/',
        '/project/<pid>/node/<nid>/files/',
    ], 'get', project_views.file.list_files, OsfWebRenderer('project/files.html', render_mako_string)),

    Rule([
        '/project/<pid>/files/<fid>/',
        '/project/<pid>/node/<nid>/files/<fid>/',
    ], 'get', project_views.file.view_file, OsfWebRenderer('project/file.html', render_mako_string)),

    # View forks
    Rule([
        '/project/<pid>/forks/',
        '/project/<pid>/node/<nid>/forks/',
    ], 'get', project_views.node.node_forks, OsfWebRenderer('project/forks.html', render_mako_string)),

    # Registrations
    Rule([
        '/project/<pid>/register/',
        '/project/<pid>/node/<nid>/register/',
    ], 'get', project_views.register.node_register_page, OsfWebRenderer('project/register.html', render_mako_string)),

    Rule([
        '/project/<pid>/register/<template>/',
        '/project/<pid>/node/<nid>/register/<template>/',
    ], 'get', project_views.register.node_register_template_page, OsfWebRenderer('project/register.html', render_mako_string)),

    Rule([
        '/project/<pid>/registrations/',
        '/project/<pid>/node/<nid>/registrations/',
    ], 'get', project_views.node.node_registrations, OsfWebRenderer('project/registrations.html', render_mako_string)),

    # Statistics
    Rule([
        '/project/<pid>/statistics/',
        '/project/<pid>/node/<nid>/statistics/',
    ], 'get', project_views.node.project_statistics, OsfWebRenderer('project/statistics.html', render_mako_string)),

    ### Wiki ###
    Rule([
        '/project/<pid>/wiki/',
        '/project/<pid>/node/<nid>/wiki/',
    ], 'get', project_views.wiki.project_wiki_home, OsfWebRenderer('project/wiki.html', render_mako_string)),

    # View
    Rule([
        '/project/<pid>/wiki/<wid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/',
    ], 'get', project_views.wiki.project_wiki_page, OsfWebRenderer('project/wiki.html', render_mako_string)),

    # Edit | GET
    Rule([
        '/project/<pid>/wiki/<wid>/edit/',
        '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
    ], 'get', project_views.wiki.project_wiki_edit, OsfWebRenderer('project/wiki/edit.html', render_mako_string)),

    # Edit | POST
    Rule([
        '/project/<pid>/wiki/<wid>/edit/',
        '/project/<pid>/node/<nid>/wiki/<wid>/edit/',
    ], 'post', project_views.wiki.project_wiki_edit_post, OsfWebRenderer('project/wiki/edit.html', render_mako_string)),

    # Compare
    Rule([
        '/project/<pid>/wiki/<wid>/compare/<compare_id>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/compare/<compare_id>/',
    ], 'get', project_views.wiki.project_wiki_compare, OsfWebRenderer('project/wiki/compare.html', render_mako_string)),

    # Versions
    Rule([
        '/project/<pid>/wiki/<wid>/version/<vid>/',
        '/project/<pid>/node/<nid>/wiki/<wid>/version/<vid>/',
    ], 'get', project_views.wiki.project_wiki_version, OsfWebRenderer('project/wiki/compare.html', render_mako_string)),

])

# API

process_rules(app, [

    Rule([
        '/project/<pid>/contributors_abbrev/',
        '/project/<pid>/node/<nid>/contributors_abbrev/',
    ], 'get', project_views.contributor.get_node_contributors_abbrev, json_renderer),

    Rule('/tags/<tag>/', 'get', project_views.tag.project_tag, json_renderer),

    Rule('/project/<pid>/', 'get', project_views.node.view_project, json_renderer),

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

    # Create
    Rule([
        '/project/new/',
        '/project/<pid>/newnode/',
    ], 'post', project_views.node.project_new_post, json_renderer),

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
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/addtag/<tag>/',
        '/project/<pid>/node/<nid>/addtag/<tag>/',
    ], 'get', project_views.tag.project_addtag, json_renderer),
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/removetag/<tag>/',
        '/project/<pid>/node/<nid>/removetag/<tag>/',
    ], 'get', project_views.tag.project_removetag, json_renderer),

    ### Files ###
    Rule([
        '/project/<pid>/files/',
        '/project/<pid>/node/<nid>/files/',
    ], 'get', project_views.file.list_files, json_renderer),

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
    Rule('/search/users/', 'post', project_views.node.search_user, json_renderer),
    Rule([
        '/project/<pid>/addcontributor/',
        '/project/<pid>/node/<nid>/addcontributor/',
    ], 'post', project_views.contributor.project_addcontributor_post, json_renderer),
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
    # TODO: Should be a POST
    Rule([
        '/project/<pid>/permissions/<permissions>/',
        '/project/<pid>/node/<nid>/permissions/<permissions>/',
    ], 'get', project_views.node.project_set_permissions, json_renderer),


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


], prefix='/api/v1')
