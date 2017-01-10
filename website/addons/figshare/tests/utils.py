import mock

from website.addons.base.testing import OAuthAddonTestCaseMixin, AddonTestCase
from website.addons.figshare.model import Figshare
from website.addons.figshare.serializer import FigshareSerializer
from website.addons.figshare.tests.factories import FigshareAccountFactory

article = {u'count': 1, u'items': [{u'status': u'Draft', u'files': [{u'thumb': None, u'download_url': u'http://files.figshare.com/1348803/0NUTZ', u'name': u'0NUTZ', u'id': 1348803, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348805/0MNXS', u'name': u'0MNXS', u'id': 1348805, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348806/0NUTZ', u'name': u'0NUTZ', u'id': 1348806, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348807/0OX1G', u'name': u'0OX1G', u'id': 1348807, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': u'http://previews.figshare.com/1350751/250_1350751.jpg', u'download_url': u'http://files.figshare.com/1350751/Selection_003.png', u'name': u'Selection_003.png', u'id': 1350751, u'mime_type': u'image/png', u'size': u'18 KB'}, {u'thumb': u'http://previews.figshare.com/1350754/250_1350754.jpg', u'download_url': u'http://files.figshare.com/1350754/Selection_003.png', u'name': u'Selection_003.png', u'id': 1350754, u'mime_type': u'image/png', u'size': u'18 KB'}], u'description': u'<p>This is made using python</p>', u'links': [], u'title': u'New fileset', u'total_size': u'34.59 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Samuel', u'last_name': u'Chrisinger', u'id': 506241, u'full_name': u'Samuel Chrisinger'}], u'defined_type': u'fileset', u'version': 15, u'categories': [{u'id': 77, u'name': u'Applied Computer Science'}], u'published_date': u'22:13, Jan 16, 2014', u'description_nohtml': u'This is made using python', u'article_id': 902210, u'tags': [{u'id': 3564, u'name': u'code'}]}]}

def create_mock_figshare(project):
    figshare_mock = mock.create_autospec(Figshare)
    figshare_mock.projects.return_value = [{u'owner': 506241, u'description': u'', u'id': 436, u'title': u'OSF Test'}]
    figshare_mock.project.return_value = {'articles': [{u'status': u'Draft', u'files': [{u'thumb': None, u'download_url': u'http://files.figshare.com/1348803/0NUTZ', u'name': u'0NUTZ', u'id': 1348803, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348805/0MNXS', u'name': u'0MNXS', u'id': 1348805, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348806/0NUTZ', u'name': u'0NUTZ', u'id': 1348806, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': None, u'download_url': u'http://files.figshare.com/1348807/0OX1G', u'name': u'0OX1G', u'id': 1348807, u'mime_type': u'text/plain', u'size': u'0 KB'}, {u'thumb': u'http://previews.figshare.com/1350751/250_1350751.jpg', u'download_url': u'http://files.figshare.com/1350751/Selection_003.png', u'name': u'Selection_003.png', u'id': 1350751, u'mime_type': u'image/png', u'size': u'18 KB'}, {u'thumb': u'http://previews.figshare.com/1350754/250_1350754.jpg', u'download_url': u'http://files.figshare.com/1350754/Selection_003.png', u'name': u'Selection_003.png', u'id': 1350754, u'mime_type': u'image/png', u'size': u'18 KB'}], u'description': u'<p>This is made using python</p>', u'links': [], u'title': u'New fileset', u'total_size': u'34.59 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Samuel', u'last_name': u'Chrisinger', u'id': 506241, u'full_name': u'Samuel Chrisinger'}], u'defined_type': u'fileset', u'version': 15, u'categories': [{u'id': 77, u'name': u'Applied Computer Science'}], u'published_date': u'22:13, Jan 16, 2014', u'description_nohtml': u'This is made using python', u'article_id': 902210, u'tags': [{u'id': 3564, u'name': u'code'}]}, {u'status': u'Drafts', u'files': [{u'id': 1404749, u'name': u'HW6.pdf', u'thumb': u'http://figshare.com/read/private/1404749/250_1404749.png', u'mime_type': u'application/pdf', u'size': u'177 KB'}], u'description': u'', u'links': [], u'title': u'HW6.pdf', u'total_size': u'172.82 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Samuel', u'last_name': u'Chrisinger', u'id': 506241, u'full_name': u'Samuel Chrisinger'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949657, u'tags': []}], u'description': u'', u'created': u'06/03/2014', u'id': 862, u'title': u'OSF Test'}
    figshare_mock.articles.return_value = article
    figshare_mock.article.return_value = article

    return figshare_mock

class FigshareAddonTestCase(OAuthAddonTestCaseMixin, AddonTestCase):

    ADDON_SHORT_NAME = 'figshare'
    ExternalAccountFactory = FigshareAccountFactory
    Provider = Figshare
    Serializer = FigshareSerializer
    client = None
    folder = {
        'path': 'fileset',
        'name': 'Memes',
        'id': '009001'
    }
