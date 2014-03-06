import mock

from website.addons.figshare.api import Figshare


def create_mock_figshare(project):
    figshare_mock = mock.create_autospec(Figshare)
    figshare_mock.article.return_value = {
        u'count': 1,
        u'items': [
            {
                u'files': [
                    {
                        u'thumb': None,
                        u'download_url': u'http: //files.figshare.com/1348803/0NUTZ',
                        u'name': u'0NUTZ',
                        u'id': 1348803,
                        u'mime_type': u'text/plain',
                        u'size': u'0KB'
                    },
                    {
                        u'thumb': None,
                        u'download_url': u'http: //files.figshare.com/1348805/0MNXS',
                        u'name': u'0MNXS',
                        u'id': 1348805,
                        u'mime_type': u'text/plain',
                        u'size': u'0KB'
                    },
                    {
                        u'thumb': None,
                        u'download_url': u'http: //files.figshare.com/1348806/0NUTZ',
                        u'name': u'0NUTZ',
                        u'id': 1348806,
                        u'mime_type': u'text/plain',
                        u'size': u'0KB'
                    },
                    {
                        u'thumb': None,
                        u'download_url': u'http: //files.figshare.com/1348807/0OX1G',
                        u'name': u'0OX1G',
                        u'id': 1348807,
                        u'mime_type': u'text/plain',
                        u'size': u'0KB'
                    },
                    {
                        u'thumb': None,
                        u'download_url': u'http: //files.figshare.com/1348808/0MNXS',
                        u'name': u'0MNXS',
                        u'id': 1348808,
                        u'mime_type': u'text/plain',
                        u'size': u'0KB'
                    },
                    {
                        u'thumb': u'http: //previews.figshare.com/1350751/250_1350751.jpg',
                        u'download_url': u'http: //files.figshare.com/1350751/Selection_003.png',
                        u'name': u'Selection_003.png',
                        u'id': 1350751,
                        u'mime_type': u'image/png',
                        u'size': u'18KB'
                    },
                    {
                        u'thumb': u'http: //previews.figshare.com/1350754/250_1350754.jpg',
                        u'download_url': u'http: //files.figshare.com/1350754/Selection_003.png',
                        u'name': u'Selection_003.png',
                        u'id': 1350754,
                        u'mime_type': u'image/png',
                        u'size': u'18KB'
                    }
                ],
                u'links': [

                ],
                u'publisher_citation': u'',
                u'defined_type': u'fileset',
                u'owner': {
                    u'id': 506241,
                    u'full_name': u'Samuel Chrisinger'
                },
                u'figshare_url': u'http://figshare.com/articles/New_fileset/902210',
                u'title': u'New fileset',
                u'total_size': u'34.69KB',
                u'master_publisher_id': 0,
                u'tags': [
                    {
                        u'id': 3564,
                        u'name': u'code'
                    }
                ],
                u'shares': 0,
                u'publisher_doi': u'',
                u'version': 15,
                u'status': u'Public',
                u'description': u'<p>Thisismadeusingpython</p>',
                u'views': 39,
                u'downloads': 0,
                u'authors': [
                    {
                        u'first_name': u'Samuel',
                        u'last_name': u'Chrisinger',
                        u'id': 506241,
                        u'full_name': u'SamuelChrisinger'
                    }
                ],
                u'description_nohtml': u'Thisismadeusingpython',
                u'article_id': 902210,
                u'categories': [
                    {
                        u'id': 77,
                        u'name': u'AppliedComputerScience'
                    }
                ],
                u'doi': u'http: //dx.doi.org/10.6084/m9.figshare.902210',
                u'published_date': u'22: 13,Jan16, 2014'
            }
        ]
    }

    figshare_mock.project.return_value = {'articles': [{u'status': u'Drafts', u'files': [{u'id': 1406369, u'name': u'faq.2', u'thumb': None, u'mime_type': u'text/html', u'size': u'12 KB'}], u'description': u'', u'links': [], u'title': u'faq.2', u'total_size': u'11.97 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'06:25, Mar 02, 2014', u'description_nohtml': u'', u'article_id': 950993, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1406368, u'name': u'explore.1', u'thumb': None, u'mime_type': u'text/html', u'size': u'10 KB'}], u'description': u'', u'links': [], u'title': u'explore.1', u'total_size': u'9.95 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'23:18, Mar 03, 2014', u'description_nohtml': u'', u'article_id': 950992, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1406367, u'name': u'getting-started.1', u'thumb': None, u'mime_type': u'text/html', u'size': u'16 KB'}], u'description': u'', u'links': [], u'title': u'getting-started.1', u'total_size': u'15.82 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'06:25, Mar 02, 2014', u'description_nohtml': u'', u'article_id': 950991, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404754, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404754/250_1404754.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}, {u'id': 1404831, u'name': u'izgFHmQ.png', u'thumb': u'http://figshare.com/read/private/1404831/250_1404831.jpg', u'mime_type': u'image/png', u'size': u'78 KB'}, {u'id': 1406371, u'name': u'explore.1', u'thumb': None, u'mime_type': u'text/html', u'size': u'10 KB'}, {u'id': 1406372, u'name': u'explore.1', u'thumb': None, u'mime_type': u'text/html', u'size': u'10 KB'}], u'description': u'', u'links': [], u'title': u'', u'total_size': u'3.22 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'fileset', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949661, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404752, u'name': u'F5NA7RK.png', u'thumb': u'http://figshare.com/read/private/1404752/250_1404752.jpg', u'mime_type': u'image/png', u'size': u'120 KB'}], u'description': u'', u'links': [], u'title': u'F5NA7RK.png', u'total_size': u'116.98 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949660, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404751, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404751/250_1404751.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}], u'description': u'', u'links': [], u'title': u'Golden_ticket_thingy.png', u'total_size': u'3.12 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949659, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404750, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404750/250_1404750.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}], u'description': u'', u'links': [], u'title': u'Golden_ticket_thingy.png', u'total_size': u'3.12 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949658, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404748, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404748/250_1404748.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}], u'description': u'', u'links': [], u'title': u'Golden_ticket_thingy.png', u'total_size': u'3.12 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949656, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404747, u'name': u'res.cls', u'thumb': None, u'mime_type': u'text/x-tex', u'size': u'25 KB'}], u'description': u'', u'links': [], u'title': u'res.cls', u'total_size': u'24.12 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949655, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404746, u'name': u'fmPeynY.jpg', u'thumb': u'http://figshare.com/read/private/1404746/250_1404746.jpg', u'mime_type': u'image/jpeg', u'size': u'382 KB'}], u'description': u'', u'links': [], u'title': u'fmPeynY.jpg', u'total_size': u'372.93 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949654, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404745, u'name': u'Fall_2013_Schedule.ods', u'thumb': None, u'mime_type': u'application/vnd.oasis.opendocument.spreadsheet', u'size': u'17 KB'}], u'description': u'', u'links': [], u'title': u'Fall_2013_Schedule.ods', u'total_size': u'16.51 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949653, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404744, u'name': u'helvetica.sty', u'thumb': None, u'mime_type': u'text/plain', u'size': u'1 KB'}], u'description': u'', u'links': [], u'title': u'helvetica.sty', u'total_size': u'1.03 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949652, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404743, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404743/250_1404743.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}], u'description': u'', u'links': [], u'title': u'Golden_ticket_thingy.png', u'total_size': u'3.12 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:19, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949651, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404742, u'name': u'Golden_ticket_thingy.png', u'thumb': u'http://figshare.com/read/private/1404742/250_1404742.jpg', u'mime_type': u'image/png', u'size': u'3.12 MB'}], u'description': u'', u'links': [], u'title': u'Golden_ticket_thingy.png', u'total_size': u'3.12 MB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'paper', u'version': 1, u'categories': [], u'published_date': u'09:25, Feb 24, 2014', u'description_nohtml': u'', u'article_id': 949650, u'tags': []}, {u'status': u'Drafts', u'files': [{u'id': 1404727, u'name': u'F5NA7RK.png', u'thumb': u'http://figshare.com/read/private/1404727/250_1404727.jpg', u'mime_type': u'image/png', u'size': u'120 KB'}], u'description': u'', u'links': [], u'title': u'F5NA7RK.png', u'total_size': u'116.98 KB', u'master_publisher_id': 0, u'authors': [{u'first_name': u'Chris', u'last_name': u'Seto', u'id': 529532, u'full_name': u'Chris Seto'}], u'defined_type': u'figure', u'version': 1, u'categories': [], u'published_date': u'15:03, Mar 01, 2014', u'description_nohtml': u'', u'article_id': 949632, u'tags': []}], u'description': u'Ignore me.', u'created': u'01/03/2014', u'id': 825, u'title': u'Test Project'}

    # figshare_mock.article_to_hgrid.return_value = [
    #     {u'status':
    #      u'Public', u'delete':
    #      u'', u'indent':
    #      0, u'description':
    #      u'This is made using python', u'tags':
    #      u'code', u'id':
    #      902210, u'versions':
    #      15, u'name':
    #      u'New fileset', u'published':
    #      u'22:13, Jan 16, 2014', u'size':
    #      u'6', u'authors':
    #      u'Samuel Chrisinger', u'download':
    #      u'', u'uploadUrl':
    #      u'/api/v1/project/{0}/figshare/article/create/902210/'.format(project), u'type':
    #      u'folder', u'parent_uid':
    #      u'null', u'uid':
    #      u'article_902210'},
    #     {u'status':
    #      u'Public', u'delete':
    #      u'/api/v1/project/{0}/figshare/article/902210/file/1348803/delete/'.format(project), u'indent':
    #      1, u'description':
    #      u'', u'tags':
    #      u'', u'id':
    #      1348803, u'versions':
    #      u'', u'name':
    #      u'0NUTZ',
    #      u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348803/0NUTZ', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348803'},
    #     {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348805/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348805, u'versions': u'', u'name': u'0MNXS',
    #      u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348805/0MNXS', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348805'},
    #     {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348806/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348806, u'versions': u'', u'name': u'0NUTZ',
    #      u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348806/0NUTZ', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348806'},
    #     {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348807/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348807, u'versions': u'', u'name': u'0OX1G',
    #      u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348807/0OX1G', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348807'},
    #     {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1350751/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1350751, u'versions': u'', u'name': u'Selection_003.png', u'published': u'', u'thumbnail':
    #      u'http://previews.figshare.com/1350751/250_1350751.jpg', u'size': u'18 KB', u'authors': u'', u'download': u'http://files.figshare.com/1350751/Selection_003.png', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1350751'},
    #     {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1350754/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1350754, u'versions': u'', u'name': u'Selection_003.png', u'published': u'', u'thumbnail': u'http://previews.figshare.com/1350754/250_1350754.jpg', u'size': u'18 KB', u'authors': u'', u'download': u'http://files.figshare.com/1350754/Selection_003.png', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1350754'}]

    return figshare_mock
