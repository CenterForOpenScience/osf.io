import logging

from framework.auth.decorators import must_be_logged_in
from osf.models import OSFUser
from website.project.views.contributor import get_node_contributors_abbrev

logger = logging.getLogger(__name__)

RESULTS_PER_PAGE = 250


@must_be_logged_in
def process_project_search_results(results, **kwargs):
    """
    :param results: list of projects from the modular ODM search
    :return: we return the entire search result, which is a list of
    dictionaries. This includes the list of contributors.
    """
    user = kwargs['auth'].user

    ret = []

    for project in results:
        authors = get_node_contributors_abbrev(project=project, auth=kwargs['auth'])
        authors_html = ''
        for author in authors['contributors']:
            a = OSFUser.load(author['user_id'])
            authors_html += f'<a href="{a.url}">{a.fullname}</a>'
            authors_html += author['separator'] + ' '
        authors_html += ' ' + authors['others_count']

        ret.append({
            'id': project._id,
            'label': project.title,
            'value': project.title,
            'category': 'My Projects' if user in project.contributors else 'Public Projects',
            'authors': authors_html,
        })

    return ret
