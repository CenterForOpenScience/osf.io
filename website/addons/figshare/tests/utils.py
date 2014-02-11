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
            u'figshare_url': u'http: //figshare.com/articles/New_fileset/902210',
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

    figshare_mock.article_to_hgrid.return_value = [
        {u'status': u'Public', u'delete': u'', u'indent': 0, u'description': u'This is made using python', u'tags': u'code', u'id': 902210, u'versions': 15, u'name': u'New fileset', u'published': u'22:13, Jan 16, 2014', u'size': u'6', u'authors': u'Samuel Chrisinger', u'download': u'', u'uploadUrl': u'/api/v1/project/{0}/figshare/article/create/902210/'.format(project), u'type': u'folder', u'parent_uid': u'null', u'uid': u'article_902210'},
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348803/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348803, u'versions': u'', u'name': u'0NUTZ', u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348803/0NUTZ', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348803'}, 
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348805/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348805, u'versions': u'', u'name': u'0MNXS', u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348805/0MNXS', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348805'}, 
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348806/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348806, u'versions': u'', u'name': u'0NUTZ', u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348806/0NUTZ', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348806'}, 
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1348807/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1348807, u'versions': u'', u'name': u'0OX1G', u'published': u'', u'thumbnail': u'', u'size': u'0 KB', u'authors': u'', u'download': u'http://files.figshare.com/1348807/0OX1G', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1348807'}, 
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1350751/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1350751, u'versions': u'', u'name': u'Selection_003.png', u'published': u'', u'thumbnail': u'http://previews.figshare.com/1350751/250_1350751.jpg', u'size': u'18 KB', u'authors': u'', u'download': u'http://files.figshare.com/1350751/Selection_003.png', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1350751'}, 
        {u'status': u'Public', u'delete': u'/api/v1/project/{0}/figshare/article/902210/file/1350754/delete/'.format(project), u'indent': 1, u'description': u'', u'tags': u'', u'id': 1350754, u'versions': u'', u'name': u'Selection_003.png', u'published': u'', u'thumbnail': u'http://previews.figshare.com/1350754/250_1350754.jpg', u'size': u'18 KB', u'authors': u'', u'download': u'http://files.figshare.com/1350754/Selection_003.png', u'uploadUrl': u'', u'type': u'file', u'parent_uid': u'article_902210', u'uid': u'file_1350754'}]

    return figshare_mock
