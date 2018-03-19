# -*- coding: utf-8 -*-
from __future__ import absolute_import
import os
import httplib as http

from flask import request
from flask import send_from_directory
from django.core.urlresolvers import reverse

from geoip import geolite2

from framework import status
from framework import sentry
from framework.auth import cas
from framework.routing import Rule
from framework.flask import redirect
from framework.routing import WebRenderer
from framework.exceptions import HTTPError
from framework.routing import json_renderer
from framework.routing import process_rules
from framework.auth import views as auth_views
from framework.routing import render_mako_string
from framework.auth.core import _get_current_user

from osf.models import Institution
from osf.utils import sanitize
from website import util
from website import prereg
from website import settings
from website import language
from website.util import metrics
from website.util import paths
from website import maintenance
from website import landing_pages as landing_page_views
from website import views as website_views
from website.citations import views as citation_views
from website.search import views as search_views
from website.oauth import views as oauth_views
from website.profile.utils import get_profile_image_url
from website.profile import views as profile_views
from website.project import views as project_views
from addons.base import views as addon_views
from website.discovery import views as discovery_views
from website.conferences import views as conference_views
from website.preprints import views as preprint_views
from website.registries import views as registries_views
from website.reviews import views as reviews_views
from website.institutions import views as institution_views
from website.notifications import views as notification_views
from website.ember_osf_web import views as ember_osf_web_views
from website.closed_challenges import views as closed_challenges_views
from website.identifiers import views as identifier_views
from website.ember_osf_web.decorators import ember_flag_is_active


def get_globals():
    """Context variables that are available for every template rendered by
    OSFWebRenderer.
    """
    user = _get_current_user()
    user_institutions = [{'id': inst._id, 'name': inst.name, 'logo_path': inst.logo_path_rounded_corners} for inst in user.affiliated_institutions.all()] if user else []
    location = geolite2.lookup(request.remote_addr) if request.remote_addr else None
    if request.host_url != settings.DOMAIN:
        try:
            inst_id = Institution.objects.get(domains__icontains=[request.host])._id
            request_login_url = '{}institutions/{}'.format(settings.DOMAIN, inst_id)
        except Institution.DoesNotExist:
            request_login_url = request.url.replace(request.host_url, settings.DOMAIN)
    else:
        request_login_url = request.url
    return {
        'private_link_anonymous': is_private_link_anonymous_view(),
        'user_name': user.username if user else '',
        'user_full_name': user.fullname if user else '',
        'user_id': user._id if user else '',
        'user_locale': user.locale if user and user.locale else '',
        'user_timezone': user.timezone if user and user.timezone else '',
        'user_url': user.url if user else '',
        'user_profile_image': get_profile_image_url(user=user, size=25) if user else '',
        'user_email_verifications': user.unconfirmed_email_info if user else [],
        'user_api_url': user.api_url if user else '',
        'user_entry_point': metrics.get_entry_point(user) if user else '',
        'user_institutions': user_institutions if user else None,
        'display_name': user.fullname if user else '',
        'anon': {
            'continent': getattr(location, 'continent', None),
            'country': getattr(location, 'country', None),
        },
        'use_cdn': settings.USE_CDN_FOR_CLIENT_LIBS,
        'sentry_dsn_js': settings.SENTRY_DSN_JS if sentry.enabled else None,
        'dev_mode': settings.DEV_MODE,
        'allow_login': settings.ALLOW_LOGIN,
        'cookie_name': settings.COOKIE_NAME,
        'status': status.pop_status_messages(),
        'prev_status': status.pop_previous_status_messages(),
        'domain': settings.DOMAIN,
        'api_domain': settings.API_DOMAIN,
        'disk_saving_mode': settings.DISK_SAVING_MODE,
        'language': language,
        'noteworthy_links_node': settings.NEW_AND_NOTEWORTHY_LINKS_NODE,
        'popular_links_node': settings.POPULAR_LINKS_NODE,
        'web_url_for': util.web_url_for,
        'api_url_for': util.api_url_for,
        'api_v2_url': util.api_v2_url,  # URL function for templates
        'api_v2_domain': settings.API_DOMAIN,
        'api_v2_base': util.api_v2_url(''),  # Base url used by JS api helper
        'sanitize': sanitize,
        'sjson': lambda s: sanitize.safe_json(s),
        'webpack_asset': paths.webpack_asset,
        'waterbutler_url': settings.WATERBUTLER_URL,
        'login_url': cas.get_login_url(request_login_url),
        'reauth_url': util.web_url_for('auth_logout', redirect_url=request.url, reauth=True),
        'profile_url': cas.get_profile_url(),
        'enable_institutions': settings.ENABLE_INSTITUTIONS,
        'keen': {
            'public': {
                'project_id': settings.KEEN['public']['project_id'],
                'write_key': settings.KEEN['public']['write_key'],
            },
            'private': {
                'project_id': settings.KEEN['private']['project_id'],
                'write_key': settings.KEEN['private']['write_key'],
            },
        },
        'maintenance': maintenance.get_maintenance(),
        'recaptcha_site_key': settings.RECAPTCHA_SITE_KEY,
        'custom_citations': settings.CUSTOM_CITATIONS,
        'osf_support_email': settings.OSF_SUPPORT_EMAIL,
        'osf_contact_email': settings.OSF_CONTACT_EMAIL,
        'wafflejs_url': '{api_domain}{waffle_url}'.format(api_domain=settings.API_DOMAIN.rstrip('/'), waffle_url=reverse('wafflejs'))
    }


def is_private_link_anonymous_view():
    # Avoid circular import
    from osf.models import PrivateLink
    try:
        return PrivateLink.objects.filter(key=request.args.get('view_only')).values_list('anonymous', flat=True).get()
    except PrivateLink.DoesNotExist:
        return False


class OsfWebRenderer(WebRenderer):
    """Render a Mako template with OSF context vars.

    :param trust: Optional. If ``False``, markup-safe escaping will be enabled
    """
    def __init__(self, *args, **kwargs):
        kwargs['data'] = get_globals
        super(OsfWebRenderer, self).__init__(*args, **kwargs)


#: Use if a view only redirects or raises error
notemplate = OsfWebRenderer('', renderer=render_mako_string, trust=False)


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

def sitemap_file(path):
    """Serves the sitemap/* files."""
    if path.endswith('.xml.gz'):
        mime = 'application/x-gzip'
    elif path.endswith('.xml'):
        mime = 'text/xml'
    else:
        raise HTTPError(http.NOT_FOUND)
    return send_from_directory(
        settings.STATIC_FOLDER + '/sitemaps/',
        path,
        mimetype=mime
    )

def ember_app(path=None):
    """Serve the contents of the ember application"""
    ember_app_folder = None
    fp = path or 'index.html'
    for k in settings.EXTERNAL_EMBER_APPS.keys():
        if request.path.strip('/').startswith(k):
            ember_app_folder = os.path.abspath(os.path.join(os.getcwd(), settings.EXTERNAL_EMBER_APPS[k]['path']))
            break

    if not ember_app_folder:
        raise HTTPError(http.NOT_FOUND)

    if not os.path.abspath(os.path.join(ember_app_folder, fp)).startswith(ember_app_folder):
        # Prevent accessing files outside of the ember build dir
        raise HTTPError(http.NOT_FOUND)

    if not os.path.isfile(os.path.join(ember_app_folder, fp)):
        fp = 'index.html'

    return send_from_directory(ember_app_folder, fp)

@ember_flag_is_active('ember_home_page')
def goodbye():
    # Redirect to dashboard if logged in
    if _get_current_user():
        return redirect(util.web_url_for('index'))
    status.push_status_message(language.LOGOUT, kind='success', trust=False)
    return {}


def make_url_map(app):
    """Set up all the routes for the OSF app.

    :param app: A Flask/Werkzeug app to bind the rules to.
    """

    # Set default views to 404, using URL-appropriate renderers
    process_rules(app, [
        Rule(
            '/<path:_>',
            ['get', 'post'],
            HTTPError(http.NOT_FOUND),
            OsfWebRenderer('', render_mako_string, trust=False)
        ),
        Rule(
            '/api/v1/<path:_>',
            ['get', 'post'],
            HTTPError(http.NOT_FOUND),
            json_renderer
        ),
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
            notemplate,
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
        Rule('/sitemaps/<path>', 'get', sitemap_file, json_renderer),
    ])

    # Ember Applications
    if settings.USE_EXTERNAL_EMBER:
        # Routes that serve up the Ember application. Hide behind feature flag.
        for prefix in settings.EXTERNAL_EMBER_APPS.keys():
            process_rules(app, [
                Rule(
                    [
                        '/<provider>/<guid>/download',
                        '/<provider>/<guid>/download/',
                    ],
                    ['get', 'post', 'put', 'patch', 'delete'],
                    website_views.resolve_guid_download,
                    notemplate,
                    endpoint_suffix='__' + prefix
                ),
            ], prefix='/' + prefix)

            process_rules(app, [
                Rule(
                    [
                        '/',
                        '/<path:path>',
                    ],
                    'get',
                    ember_app,
                    json_renderer,
                    endpoint_suffix='__' + prefix
                ),
            ], prefix='/' + prefix)

        if settings.EXTERNAL_EMBER_APPS.get('ember_osf_web'):
            process_rules(app, [
                Rule(
                    ember_osf_web_views.routes,
                    'get',
                    ember_osf_web_views.use_ember_app,
                    notemplate
                )
            ])

    ### Base ###

    process_rules(app, [

        Rule(
            '/dashboard/',
            'get',
            website_views.dashboard,
            OsfWebRenderer('home.mako', trust=False)
        ),

        Rule(
            '/myprojects/',
            'get',
            website_views.my_projects,
            OsfWebRenderer('my_projects.mako', trust=False)
        ),

        Rule(
            '/reproducibility/',
            'get',
            website_views.reproducibility,
            notemplate
        ),
        Rule('/about/', 'get', website_views.redirect_about, notemplate),
        Rule('/help/', 'get', website_views.redirect_help, notemplate),
        Rule('/faq/', 'get', website_views.redirect_faq, notemplate),
        Rule(['/getting-started/', '/getting-started/email/', '/howosfworks/'], 'get', website_views.redirect_getting_started, notemplate),
        Rule('/support/', 'get', website_views.support, OsfWebRenderer('public/pages/support.mako', trust=False)),
        Rule(
            '/explore/',
            'get',
            discovery_views.redirect_explore_to_activity,
            notemplate
        ),

        Rule(
            [
                '/messages/',
            ],
            'get',
            {},
            OsfWebRenderer('public/comingsoon.mako', trust=False)
        ),

        Rule(
            '/view/<meeting>/',
            'get',
            conference_views.conference_results,
            OsfWebRenderer('public/pages/meeting.mako', trust=False),
        ),

        Rule(
            '/view/<meeting>/plain/',
            'get',
            conference_views.conference_results,
            OsfWebRenderer('public/pages/meeting_plain.mako', trust=False),
            endpoint_suffix='__plain',
        ),

        Rule(
            '/api/v1/view/<meeting>/',
            'get',
            conference_views.conference_data,
            json_renderer,
        ),

        Rule(
            '/meetings/',
            'get',
            conference_views.conference_view,
            OsfWebRenderer('public/pages/meeting_landing.mako', trust=False),
        ),

        Rule(
            '/api/v1/meetings/submissions/',
            'get',
            conference_views.conference_submissions,
            json_renderer,
        ),

        Rule(
            '/presentations/',
            'get',
            conference_views.redirect_to_meetings,
            json_renderer,
        ),

        Rule(
            '/news/',
            'get',
            website_views.redirect_to_cos_news,
            notemplate
        ),

        Rule(
            '/erpc/',
            'get',
            closed_challenges_views.erpc_landing_page,
            OsfWebRenderer('erpc_landing_page.mako', trust=False)
        ),

        Rule(
            '/prereg/',
            'get',
            prereg.prereg_landing_page,
            OsfWebRenderer('prereg_landing_page.mako', trust=False)
        ),

        Rule(
            '/preprints/',
            'get',
            preprint_views.preprint_landing_page,
            OsfWebRenderer('public/pages/preprint_landing.mako', trust=False),
        ),

        Rule(
            '/registries/',
            'get',
            registries_views.registries_landing_page,
            OsfWebRenderer('public/pages/registries_landing.mako', trust=False),
        ),

        Rule(
            '/reviews/',
            'get',
            reviews_views.reviews_landing_page,
            OsfWebRenderer('public/pages/reviews_landing.mako', trust=False),
        ),

        Rule(
            '/preprint/',
            'get',
            preprint_views.preprint_redirect,
            notemplate,
        ),

        Rule(
            '/api/v1/<campaign>/draft_registrations/',
            'get',
            prereg.prereg_draft_registrations,
            json_renderer,
        ),
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
            OsfWebRenderer('util/oauth_complete.mako', trust=False),
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
        Rule('/confirmed_emails/', 'put', auth_views.unconfirmed_email_add, json_renderer),
        Rule('/confirmed_emails/', 'delete', auth_views.unconfirmed_email_remove, json_renderer)

    ], prefix='/api/v1')

    ### Metadata ###
    process_rules(app, [

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
        Rule('/forms/signin/', 'get', website_views.signin_form, json_renderer),
        Rule('/forms/forgot_password/', 'get', website_views.forgot_password_form, json_renderer),
    ], prefix='/api/v1')

    ### Discovery ###

    process_rules(app, [

        Rule(
            '/explore/activity/',
            'get',
            discovery_views.redirect_explore_activity_to_activity,
            notemplate
        ),

        Rule(
            '/activity/',
            'get',
            discovery_views.activity,
            OsfWebRenderer('public/pages/active_nodes.mako', trust=False)
        ),
    ])

    ### Auth ###

    process_rules(app, [

        # confirm email
        Rule(
            '/confirm/<uid>/<token>/',
            'get',
            auth_views.confirm_email_get,
            notemplate
        ),

        # confirm email for login through external identity provider
        Rule(
            '/confirm/external/<uid>/<token>/',
            'get',
            auth_views.external_login_confirm_email_get,
            notemplate
        ),

        # reset password get
        Rule(
            '/resetpassword/<uid>/<token>/',
            'get',
            auth_views.reset_password_get,
            OsfWebRenderer('public/resetpassword.mako', render_mako_string, trust=False)
        ),

        # reset password post
        Rule(
            '/resetpassword/<uid>/<token>/',
            'post',
            auth_views.reset_password_post,
            OsfWebRenderer('public/resetpassword.mako', render_mako_string, trust=False)
        ),

        # resend confirmation get
        Rule(
            '/resend/',
            'get',
            auth_views.resend_confirmation_get,
            OsfWebRenderer('resend.mako', render_mako_string, trust=False)
        ),

        # resend confirmation post
        Rule(
            '/resend/',
            'post',
            auth_views.resend_confirmation_post,
            OsfWebRenderer('resend.mako', render_mako_string, trust=False)

        ),

        # oauth user email get
        Rule(
            '/external-login/email',
            'get',
            auth_views.external_login_email_get,
            OsfWebRenderer('external_login_email.mako', render_mako_string, trust=False)
        ),

        # oauth user email post
        Rule(
            '/external-login/email',
            'post',
            auth_views.external_login_email_post,
            OsfWebRenderer('external_login_email.mako', render_mako_string, trust=False)
        ),

        # user sign up page
        Rule(
            '/register/',
            'get',
            auth_views.auth_register,
            OsfWebRenderer('public/register.mako', trust=False)
        ),

        # osf login and campaign login
        Rule(
            [
                '/login/',
                '/account/'
            ],
            'get',
            auth_views.auth_login,
            notemplate
        ),

        # create user account via api
        Rule(
            '/api/v1/register/',
            'post',
            auth_views.register_user,
            json_renderer
        ),

        # osf logout and cas logout
        Rule(
            '/logout/',
            'get',
            auth_views.auth_logout,
            notemplate
        ),

        # forgot password get
        Rule(
            '/forgotpassword/',
            'get',
            auth_views.forgot_password_get,
            OsfWebRenderer('public/forgot_password.mako', trust=False)
        ),

        # forgot password post
        Rule(
            '/forgotpassword/',
            'post',
            auth_views.forgot_password_post,
            OsfWebRenderer('public/forgot_password.mako', trust=False)
        ),

        Rule(
            '/login/connected_tools/',
            'get',
            landing_page_views.connected_tools,
            notemplate
        ),

        Rule(
            '/login/enriched_profile/',
            'get',
            landing_page_views.enriched_profile,
            notemplate
        ),

    ])

    ### Profile ###

    # Web

    process_rules(app, [
        Rule(
            '/profile/',
            'get',
            profile_views.profile_view,
            OsfWebRenderer('profile.mako', trust=False)
        ),

        Rule(
            '/profile/<uid>/',
            'get',
            profile_views.profile_view_id,
            OsfWebRenderer('profile.mako', trust=False)
        ),

        # unregistered user claim account (contributor-ship of a project)
        # user will be required to set email and password
        # claim token must be present in query parameter
        Rule(
            ['/user/<uid>/<pid>/claim/'],
            ['get', 'post'],
            project_views.contributor.claim_user_form,
            OsfWebRenderer('claim_account.mako', trust=False)
        ),

        # registered user claim account (contributor-ship of a project)
        # user will be required to verify password
        # claim token must be present in query parameter
        Rule(
            ['/user/<uid>/<pid>/claim/verify/<token>/'],
            ['get', 'post'],
            project_views.contributor.claim_user_registered,
            OsfWebRenderer('claim_account_registered.mako', trust=False)
        ),

        Rule(
            '/settings/',
            'get',
            profile_views.user_profile,
            OsfWebRenderer('profile/settings.mako', trust=False),
        ),

        Rule(
            [
                '/project/<pid>/addons/',
                '/project/<pid>/node/<nid>/addons/',
            ],
            'get',
            project_views.node.node_addons,
            OsfWebRenderer('project/addons.mako', trust=False)
        ),
        Rule(
            '/settings/account/',
            'get',
            profile_views.user_account,
            OsfWebRenderer('profile/account.mako', trust=False),
        ),

        Rule(
            '/settings/account/password',
            'post',
            profile_views.user_account_password,
            OsfWebRenderer('profile/account.mako', trust=False),
        ),

        Rule(
            '/settings/addons/',
            'get',
            profile_views.user_addons,
            OsfWebRenderer('profile/addons.mako', trust=False),
        ),

        Rule(
            '/settings/notifications/',
            'get',
            profile_views.user_notifications,
            OsfWebRenderer('profile/notifications.mako', trust=False),
        ),

        Rule(
            '/settings/applications/',
            'get',
            profile_views.oauth_application_list,
            OsfWebRenderer('profile/oauth_app_list.mako', trust=False)
        ),

        Rule(
            '/settings/applications/create/',
            'get',
            profile_views.oauth_application_register,
            OsfWebRenderer('profile/oauth_app_detail.mako', trust=False)
        ),

        Rule(
            '/settings/applications/<client_id>/',
            'get',
            profile_views.oauth_application_detail,
            OsfWebRenderer('profile/oauth_app_detail.mako', trust=False)
        ),

        Rule(
            '/settings/tokens/',
            'get',
            profile_views.personal_access_token_list,
            OsfWebRenderer('profile/personal_tokens_list.mako', trust=False)
        ),

        Rule(
            '/settings/tokens/create/',
            'get',
            profile_views.personal_access_token_register,
            OsfWebRenderer('profile/personal_tokens_detail.mako', trust=False)
        ),

        Rule(
            '/settings/tokens/<_id>/',
            'get',
            profile_views.personal_access_token_detail,
            OsfWebRenderer('profile/personal_tokens_detail.mako', trust=False)
        )
    ])

    # API

    process_rules(app, [

        Rule('/profile/', 'get', profile_views.profile_view_json, json_renderer),
        Rule('/profile/', 'put', profile_views.update_user, json_renderer),
        Rule('/resend/', 'put', profile_views.resend_confirmation, json_renderer),
        Rule('/profile/<uid>/', 'get', profile_views.profile_view_id_json, json_renderer),

        # Used by profile.html
        Rule('/user/<uid>/<pid>/claim/email/', 'post',
             project_views.contributor.claim_user_post, json_renderer),

        Rule(
            '/profile/export/',
            'post',
            profile_views.request_export,
            json_renderer,
        ),

        Rule(
            '/profile/deactivate/',
            'post',
            profile_views.request_deactivation,
            json_renderer,
        ),
        Rule(
            '/profile/cancel_request_deactivation/',
            'post',
            profile_views.cancel_request_deactivation,
            json_renderer,
        ),

        Rule(
            '/profile/logins/',
            'patch',
            profile_views.delete_external_identity,
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

        Rule(
            '/search/',
            'get',
            search_views.search_view,
            OsfWebRenderer('search.mako', trust=False)
        ),
        Rule(
            '/share/registration/',
            'get',
            {'register': settings.SHARE_REGISTRATION_URL},
            json_renderer
        ),
        Rule(
            '/api/v1/user/search/',
            'get', search_views.search_contributor,
            json_renderer
        ),
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
        Rule('/share/search/', 'get', website_views.legacy_share_v1_search, json_renderer),

    ], prefix='/api/v1')

    # Institution

    process_rules(app, [
        Rule('/institutions/<inst_id>/', 'get', institution_views.view_institution, OsfWebRenderer('institution.mako', trust=False))
    ])

    # Project

    # Web

    process_rules(app, [
        # '/' route loads home.mako if logged in, otherwise loads landing.mako
        Rule('/', 'get', website_views.index, OsfWebRenderer('index.mako', trust=False)),

        Rule('/goodbye/', 'get', goodbye, OsfWebRenderer('landing.mako', trust=False)),

        Rule(
            [
                '/project/<pid>/',
                '/project/<pid>/node/<nid>/',
            ],
            'get',
            project_views.node.view_project,
            OsfWebRenderer('project/project.mako', trust=False)
        ),

        # Create a new subproject/component
        Rule(
            '/project/<pid>/newnode/',
            'post',
            project_views.node.project_new_node,
            notemplate
        ),

        Rule('/project/new/<pid>/beforeTemplate/', 'get',
             project_views.node.project_before_template, json_renderer),

        Rule(
            [
                '/project/<pid>/contributors/',
                '/project/<pid>/node/<nid>/contributors/',
            ],
            'get',
            project_views.node.node_contributors,
            OsfWebRenderer('project/contributors.mako', trust=False),
        ),

        Rule(
            [
                '/project/<pid>/settings/',
                '/project/<pid>/node/<nid>/settings/',
            ],
            'get',
            project_views.node.node_setting,
            OsfWebRenderer('project/settings.mako', trust=False)
        ),

        # Permissions
        Rule(  # TODO: Where, if anywhere, is this route used?
            [
                '/project/<pid>/permissions/<permissions>/',
                '/project/<pid>/node/<nid>/permissions/<permissions>/',
            ],
            'post',
            project_views.node.project_set_privacy,
            OsfWebRenderer('project/project.mako', trust=False)
        ),

        ### Logs ###

        # View forks
        Rule(
            [
                '/project/<pid>/forks/',
                '/project/<pid>/node/<nid>/forks/',
            ],
            'get',
            project_views.node.node_forks,
            OsfWebRenderer('project/forks.mako', trust=False)
        ),

        # Registrations
        Rule(
            [
                '/project/<pid>/register/',
                '/project/<pid>/node/<nid>/register/',
            ],
            'get',
            project_views.register.node_register_page,
            OsfWebRenderer('project/register.mako', trust=False)
        ),

        Rule(
            [
                '/project/<pid>/register/<metaschema_id>/',
                '/project/<pid>/node/<nid>/register/<metaschema_id>/',
            ],
            'get',
            project_views.register.node_register_template_page,
            OsfWebRenderer('project/register.mako', trust=False)
        ),
        Rule(
            [
                '/project/<pid>/registrations/',
                '/project/<pid>/node/<nid>/registrations/',
            ],
            'get',
            project_views.node.node_registrations,
            OsfWebRenderer('project/registrations.mako', trust=False)
        ),
        Rule(
            [
                '/project/<pid>/registrations/',
                '/project/<pid>/node/<nid>/registrations/',
            ],
            'post',
            project_views.drafts.new_draft_registration,
            OsfWebRenderer('project/edit_draft_registration.mako', trust=False)),
        Rule(
            [
                '/project/<pid>/drafts/<draft_id>/',
                '/project/<pid>/node/<nid>/drafts/<draft_id>/',
            ],
            'get',
            project_views.drafts.edit_draft_registration_page,
            OsfWebRenderer('project/edit_draft_registration.mako', trust=False)),
        Rule(
            [
                '/project/<pid>/drafts/<draft_id>/register/',
                '/project/<pid>/node/<nid>/drafts/<draft_id>/register/',
            ],
            'get',
            project_views.drafts.draft_before_register_page,
            OsfWebRenderer('project/register_draft.mako', trust=False)),

        Rule(
            [
                '/project/<pid>/retraction/',
                '/project/<pid>/node/<nid>/retraction/',
            ],
            'get',
            project_views.register.node_registration_retraction_redirect,
            notemplate,
        ),

        Rule(
            [
                '/project/<pid>/withdraw/',
                '/project/<pid>/node/<nid>/withdraw/',
            ],
            'get',
            project_views.register.node_registration_retraction_get,
            OsfWebRenderer('project/retract_registration.mako', trust=False)
        ),

        Rule(
            '/ids/<category>/<path:value>/',
            'get',
            project_views.register.get_referent_by_identifier,
            notemplate,
        ),

        Rule(
            [
                '/project/<pid>/analytics/',
                '/project/<pid>/node/<nid>/analytics/',
            ],
            'get',
            project_views.node.project_statistics,
            OsfWebRenderer('project/statistics.mako', trust=False)
        ),

        ### Files ###

        # Note: Web endpoint for files view must pass `mode` = `page` to
        # include project view data and JS includes
        # TODO: Start waterbutler to test
        Rule(
            [
                '/project/<pid>/files/',
                '/project/<pid>/node/<nid>/files/',
            ],
            'get',
            project_views.file.collect_file_trees,
            OsfWebRenderer('project/files.mako', trust=False),
            view_kwargs={'mode': 'page'},
        ),
        Rule(
            [
                '/project/<pid>/files/<provider>/<path:path>/',
                '/project/<pid>/node/<nid>/files/<provider>/<path:path>/',
            ],
            'get',
            addon_views.addon_view_or_download_file,
            OsfWebRenderer('project/view_file.mako', trust=False)
        ),
        Rule(
            '/download/<fid_or_guid>/',
            'get',
            addon_views.persistent_file_download,
            json_renderer,
        ),
        Rule(
            [
                '/api/v1/project/<pid>/files/<provider>/<path:path>/',
                '/api/v1/project/<pid>/node/<nid>/files/<provider>/<path:path>/',
            ],
            'get',
            addon_views.addon_view_or_download_file,
            json_renderer
        ),
        Rule(
            [
                '/project/<pid>/files/deleted/<trashed_id>/',
                '/project/<pid>/node/<nid>/files/deleted/<trashed_id>/',
            ],
            'get',
            addon_views.addon_deleted_file,
            OsfWebRenderer('project/view_file.mako', trust=False)
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
            ],
            'get',
            addon_views.addon_view_or_download_file_legacy,
            OsfWebRenderer('project/view_file.mako', trust=False),
        ),
        Rule(
            [
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
        Rule(
            [
                '/quickfiles/<fid>/'
            ],
            'get',
            addon_views.addon_view_or_download_quickfile,
            json_renderer
        )
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

        # Create project, used by [coming replacement]
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
                '/project/<pid>/pointer/',
                '/project/<pid>/node/<nid>pointer/',
            ],
            'delete',
            project_views.node.remove_pointer,
            json_renderer,
        ),

        # Draft Registrations
        Rule([
            '/project/<pid>/drafts/',
        ], 'get', project_views.drafts.get_draft_registrations, json_renderer),
        Rule([
            '/project/<pid>/drafts/<draft_id>/',
        ], 'get', project_views.drafts.get_draft_registration, json_renderer),
        Rule([
            '/project/<pid>/drafts/<draft_id>/',
        ], 'put', project_views.drafts.update_draft_registration, json_renderer),
        Rule([
            '/project/<pid>/drafts/<draft_id>/',
        ], 'delete', project_views.drafts.delete_draft_registration, json_renderer),
        Rule([
            '/project/<pid>/drafts/<draft_id>/submit/',
        ], 'post', project_views.drafts.submit_draft_for_review, json_renderer),

        # Meta Schemas
        Rule([
            '/project/drafts/schemas/',
        ], 'get', project_views.drafts.get_metaschemas, json_renderer),

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

        Rule(
            [
                '/project/<pid>/contributor/remove/',
                '/project/<pid>/node/<nid>/contributor/remove/',
            ],
            'POST',
            project_views.contributor.project_remove_contributor,
            json_renderer,
        ),

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

        # Update
        Rule(
            [
                '/project/<pid>/',
                '/project/<pid>/node/<nid>/',
            ],
            'put',
            project_views.node.update_node,
            json_renderer,
        ),

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

        # Reorder components
        Rule('/project/<pid>/reorder_components/', 'post',
             project_views.node.project_reorder_components, json_renderer),

        # Edit node
        Rule([
            '/project/<pid>/edit/',
            '/project/<pid>/node/<nid>/edit/',
        ], 'post', project_views.node.edit_node, json_renderer),

        # Add / remove tags
        Rule([
            '/project/<pid>/tags/',
            '/project/<pid>/node/<nid>/tags/',
            '/project/<pid>/tags/<tag>/',
            '/project/<pid>/node/<nid>/tags/<tag>/',
        ], 'post', project_views.tag.project_add_tag, json_renderer),
        Rule([
            '/project/<pid>/tags/',
            '/project/<pid>/node/<nid>/tags/',
            '/project/<pid>/tags/<tag>/',
            '/project/<pid>/node/<nid>/tags/<tag>/',
        ], 'delete', project_views.tag.project_remove_tag, json_renderer),

        # Add / remove contributors
        Rule([
            '/project/<pid>/contributors/',
            '/project/<pid>/node/<nid>/contributors/',
        ], 'post', project_views.contributor.project_contributors_post, json_renderer),
        # Forks
        Rule(
            [
                '/project/<pid>/fork/before/',
                '/project/<pid>/node/<nid>/fork/before/',
            ], 'get', project_views.node.project_before_fork, json_renderer,
        ),
        Rule(
            [
                '/project/<pid>/pointer/fork/',
                '/project/<pid>/node/<nid>/pointer/fork/',
            ], 'post', project_views.node.fork_pointer, json_renderer,
        ),

        # Registrations
        Rule([
            '/project/<pid>/beforeregister/',
            '/project/<pid>/node/<nid>/beforeregister',
        ], 'get', project_views.register.project_before_register, json_renderer),
        Rule([
            '/project/<pid>/drafts/<draft_id>/register/',
            '/project/<pid>/node/<nid>/drafts/<draft_id>/register/',
        ], 'post', project_views.drafts.register_draft_registration, json_renderer),
        Rule([
            '/project/<pid>/withdraw/',
            '/project/<pid>/node/<nid>/withdraw/'
        ], 'post', project_views.register.node_registration_retraction_post, json_renderer),

        Rule(
            [
                '/project/<pid>/identifiers/',
                '/project/<pid>/node/<nid>/identifiers/',
            ],
            'post',
            identifier_views.node_identifiers_post,
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
                '/registration/<pid>/callbacks/',
            ],
            'put',
            project_views.register.registration_callbacks,
            json_renderer,
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
            [
                '/project/<pid>/tree/',
                '/project/<pid>/node/<nid>/tree/'
            ],
            'get',
            project_views.node.get_node_tree,
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
        )
    ], prefix='/api/v1')

    # Set up static routing for addons
    # NOTE: We use nginx to serve static addon assets in production
    addon_base_path = os.path.abspath('addons')
    if settings.DEV_MODE:
        from flask import stream_with_context, Response
        import requests

        @app.route('/static/addons/<addon>/<path:filename>')
        def addon_static(addon, filename):
            addon_path = os.path.join(addon_base_path, addon, 'static')
            return send_from_directory(addon_path, filename)

        @app.route('/ember-cli-live-reload.js')
        def ember_cli_live_reload():
            req = requests.get('{}/ember-cli-live-reload.js'.format(settings.LIVE_RELOAD_DOMAIN), stream=True)
            return Response(stream_with_context(req.iter_content()), content_type=req.headers['content-type'])
