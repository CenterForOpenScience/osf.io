import logging

import gitlab
from gitlab.exceptions import GitlabError
GitlabError = GitlabError

from website import settings

import settings as gitlab_settings


logger = logging.getLogger(__name__)

if gitlab_settings.HOST and gitlab_settings.TOKEN:
    client = gitlab.Gitlab(
        gitlab_settings.HOST,
        token=gitlab_settings.TOKEN,
        verify_ssl=gitlab_settings.VERIFY_SSL,
    )
else:
    # Create dummy client for testing; GitLab constructor requires a domain
    logger.warn('Creating dummy GitLab client')
    client = gitlab.Gitlab(settings.DOMAIN)
