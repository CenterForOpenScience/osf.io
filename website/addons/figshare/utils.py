def project_to_hgrid(node, project):
    return [article_to_hgrid(node, article) for article in project['articles']]


def article_to_hgrid(node, article, expand=False):
    if article['defined_type'] == 'fileset':
        if expand:
            return [file_to_hgrid(node, article, item) for item in article['files']]
        return {
            'name': article['title'] or article['article_id'],  # Is often blank?
            'kind': 'folder',  # TODO Change me
            #'published': article['published_date'],
            #'tags': ', '.join([tag['name'] for tag in article['tags']]),
            #'description': article['description_nohtml'],
            #'authors': ', '.join([author['full_name'] for author in article['authors']]),
            #'status': article['status'],
            #'versions': article['version'],
            #'size': str(len(article['files'])),
            'urls':  {
                'upload': '{base}figshare/create/article/{aid}/'.format(base=node.api_url, aid=article['article_id']),
                'delete': node.api_url + 'figshare/' + str(article['article_id']) + '/file/{id}/delete/',
                'download': '',
                'fetch': '{base}figshare/hgrid/article/{aid}'.format(base=node.api_url, aid=article['article_id']),
                'view': ''
            },
            'permissions': {
                'edit': True if article['status'] == 'Public' else False,
                'view': True,
                'download': True if article['status'] == 'Public' else False
            }
        }
    else:
        return file_to_hgrid(node, article, article['files'][0])


def file_to_hgrid(node, article, item):

    urls = {
        'upload': '',
        'delete': '',
        'download': item.get('download_url'),
        'view': '{base}figshare/article/{aid}/file/{fid}'.format(base=node.api_url, aid=article['article_id'], fid=item.get('id'))
    }
    permissions = {
        'edit': False,
        'view': True,
        'download': article['status'] == 'Public'
    }

    return {
        'name': item['name'],
        'kind': 'file',
        'published': '',
        'tags': '',
        'description': '',
        'authors': '',
        'status': article['status'],
        'versions': '',
        'urls':  urls,
        'permissions': permissions,
        'size': item.get('size'),
        'thumbnail': item.get('thumb') or '',
    }


# TODO Finish me
def build_figshare_urls(node, project_id, file_id=None):
    urls = {
        'upload': '',
        'delete': '',
        'download': '',
        'view': ''
    }
    return urls
