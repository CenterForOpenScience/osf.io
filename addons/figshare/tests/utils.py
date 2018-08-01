import mock

from addons.base.tests.base import OAuthAddonTestCaseMixin, AddonTestCase
from addons.figshare.models import FigshareProvider
from addons.figshare.tests.factories import FigshareAccountFactory
from addons.figshare.serializer import FigshareSerializer

article = {'count': 1, 'items': [{'status': 'Draft', 'files': [{'thumb': None, 'download_url': 'http://files.figshare.com/1348803/0NUTZ', 'name': '0NUTZ', 'id': 1348803, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348805/0MNXS', 'name': '0MNXS', 'id': 1348805, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348806/0NUTZ', 'name': '0NUTZ', 'id': 1348806, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348807/0OX1G', 'name': '0OX1G', 'id': 1348807, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': 'http://previews.figshare.com/1350751/250_1350751.jpg', 'download_url': 'http://files.figshare.com/1350751/Selection_003.png', 'name': 'Selection_003.png', 'id': 1350751, 'mime_type': 'image/png', 'size': '18 KB'}, {'thumb': 'http://previews.figshare.com/1350754/250_1350754.jpg', 'download_url': 'http://files.figshare.com/1350754/Selection_003.png', 'name': 'Selection_003.png', 'id': 1350754, 'mime_type': 'image/png', 'size': '18 KB'}], 'description': '<p>This is made using python</p>', 'links': [], 'title': 'New fileset', 'total_size': '34.59 KB', 'master_publisher_id': 0, 'authors': [{'first_name': 'Samuel', 'last_name': 'Chrisinger', 'id': 506241, 'full_name': 'Samuel Chrisinger'}], 'defined_type': 'fileset', 'version': 15, 'categories': [{'id': 77, 'name': 'Applied Computer Science'}], 'published_date': '22:13, Jan 16, 2014', 'description_nohtml': 'This is made using python', 'article_id': 902210, 'tags': [{'id': 3564, 'name': 'code'}]}]}

def create_mock_figshare(project):
    figshare_mock = mock.create_autospec(FigshareProvider)
    figshare_mock.projects.return_value = [{'owner': 506241, 'description': '', 'id': 436, 'title': 'OSF Test'}]
    figshare_mock.project.return_value = {'articles': [{'status': 'Draft', 'files': [{'thumb': None, 'download_url': 'http://files.figshare.com/1348803/0NUTZ', 'name': '0NUTZ', 'id': 1348803, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348805/0MNXS', 'name': '0MNXS', 'id': 1348805, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348806/0NUTZ', 'name': '0NUTZ', 'id': 1348806, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': None, 'download_url': 'http://files.figshare.com/1348807/0OX1G', 'name': '0OX1G', 'id': 1348807, 'mime_type': 'text/plain', 'size': '0 KB'}, {'thumb': 'http://previews.figshare.com/1350751/250_1350751.jpg', 'download_url': 'http://files.figshare.com/1350751/Selection_003.png', 'name': 'Selection_003.png', 'id': 1350751, 'mime_type': 'image/png', 'size': '18 KB'}, {'thumb': 'http://previews.figshare.com/1350754/250_1350754.jpg', 'download_url': 'http://files.figshare.com/1350754/Selection_003.png', 'name': 'Selection_003.png', 'id': 1350754, 'mime_type': 'image/png', 'size': '18 KB'}], 'description': '<p>This is made using python</p>', 'links': [], 'title': 'New fileset', 'total_size': '34.59 KB', 'master_publisher_id': 0, 'authors': [{'first_name': 'Samuel', 'last_name': 'Chrisinger', 'id': 506241, 'full_name': 'Samuel Chrisinger'}], 'defined_type': 'fileset', 'version': 15, 'categories': [{'id': 77, 'name': 'Applied Computer Science'}], 'published_date': '22:13, Jan 16, 2014', 'description_nohtml': 'This is made using python', 'article_id': 902210, 'tags': [{'id': 3564, 'name': 'code'}]}, {'status': 'Drafts', 'files': [{'id': 1404749, 'name': 'HW6.pdf', 'thumb': 'http://figshare.com/read/private/1404749/250_1404749.png', 'mime_type': 'application/pdf', 'size': '177 KB'}], 'description': '', 'links': [], 'title': 'HW6.pdf', 'total_size': '172.82 KB', 'master_publisher_id': 0, 'authors': [{'first_name': 'Samuel', 'last_name': 'Chrisinger', 'id': 506241, 'full_name': 'Samuel Chrisinger'}], 'defined_type': 'paper', 'version': 1, 'categories': [], 'published_date': '09:25, Feb 24, 2014', 'description_nohtml': '', 'article_id': 949657, 'tags': []}], 'description': '', 'created': '06/03/2014', 'id': 862, 'title': 'OSF Test'}
    figshare_mock.articles.return_value = article
    figshare_mock.article.return_value = article

    return figshare_mock

class FigshareAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'figshare'
    ExternalAccountFactory = FigshareAccountFactory
    Provider = FigshareProvider
    Serializer = FigshareSerializer
    client = None
    folder = {
        'path': 'fileset',
        'name': 'Memes',
        'id': '009001'
    }
