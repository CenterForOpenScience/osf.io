# -*- coding: utf-8 -*-
"""
Base settings file, common to all environments.
These settings can be overridden in local.py.
"""

from website import settings

DISCOURSE_SSO_SECRET = 'changeme'
DISCOURSE_SERVER_URL = 'http://192.168.99.100/'
DISCOURSE_API_KEY = 'changeme'
DISCOURSE_API_ADMIN_USER = 'system'

DISCOURSE_CATEGORY_COLORS = {
    'Files': 'BF1E2E',
    'Wikis': '3AB54A',
    'Projects': '652D90'
}

DISCOURSE_LOG_REQUESTS = False

DISCOURSE_SERVER_SETTINGS = {'title': 'Open Science Framework',
                             'site_description': 'A scholarly commons to connect the entire research cycle',
                             'contact_email': 'changeme',
                             'contact_url': 'https://cos.io/contact/',
                             'company_short_name': 'COS',
                             'company_full_name': 'Center for Open Science',
                             'company_domain': 'osf.io',
                             'exclude_rel_nofollow_domains': 'osf.io|cos.io',
                             'notification_email': 'noreply@osf.io',
                             'site_contact_username': 'system',
                             'logo_url': settings.DOMAIN + 'static/img/cos-white2.png',
                             'logo_small_url': settings.DOMAIN + 'static/img/cos-white2.png',
                             'favicon_url': settings.DOMAIN + 'favicon.ico',
                             'enable_local_logins': 'false',
                             'enable_sso': 'true',
                             'sso_url': settings.API_DOMAIN + 'v2/sso',
                             'sso_secret': DISCOURSE_SSO_SECRET,
                             'sso_overrides_email': 'true',
                             'sso_overrides_username': 'true',
                             'sso_overrides_name': 'true',
                             'sso_overrides_avatar': 'true',
                             'allow_uploaded_avatars': 'false',
                             'logout_redirect': settings.DOMAIN + 'logout',
                             'cors_origins': settings.DOMAIN.strip('/'),
                             'min_topic_title_length': '0',
                             'title_min_entropy': '0',
                             'title_prettify': 'false',
                             'allow_duplicate_topic_titles': 'true',
                             'allow_uppercase_posts': 'true',
                             'tagging_enabled': 'false',
                             'max_tag_length': '100',
                             'max_tags_per_topic': '20',
                             'min_trust_level_to_tag_topics': '4',
                             'full_name_required': 'true',
                             'prioritize_username_in_ux': 'false',
                             'display_name_on_posts': 'true',
                             'osf_domain': settings.DOMAIN,
                             'mfr_domain': settings.MFR_SERVER_URL,
 }
