# from bson import ObjectId
# from . import database_source as database

# todo import correct database
# todo generate links from odm schemas

project_url_file = 'project-urls.txt'
profile_url_file = 'profile-urls.txt'

def _get_dashboard_url(project, parent_id=None):

    if parent_id:
        return '/project/{pid}/node/{nid}/'.format(
            pid=parent_id,
            nid=project['_id']
        )

    return '/project/{pid}/'.format(
        pid=project['_id']
    )

def generate_basic_urls(project, parent_id=None):

    urls = []

    dashboard_url = _get_dashboard_url(project, parent_id)

    urls.append(dashboard_url)

    urls.extend([
        '{dashboard}statistics'.format(dashboard=dashboard_url),
        '{dashboard}registrations'.format(dashboard=dashboard_url),
        '{dashboard}forks'.format(dashboard=dashboard_url),
        '{dashboard}settings'.format(dashboard=dashboard_url),
    ])

    if 'registered_meta' in project and project['registered_meta']:
        urls.append('{dashboard}register/{registration}'.format(
            dashboard=dashboard_url,
            registration=project['registered_meta'].keys()[0]
        ))

    return urls

def generate_file_urls(project, parent_id=None):

    urls = []
    
    if 'files_current' not in project:
        return urls

    dashboard_url = _get_dashboard_url(project, parent_id)

    for file_name, file_id in project['files_current'].items():
        file_record = database['nodefile'].find_one({'_id' : ObjectId(file_id)})
        current_url = '{dashboard}files/{name}'.format(
            dashboard=dashboard_url,
            pid=project['_id'],
            name=file_record['path']
        )
        urls.append(current_url)
        try:
            nversions = len(project['files_versions'][file_name])
            for version in range(1, nversions + 1):
                urls.append('{dashboard}files/download/{name}/version/{version}'.format(
                    dashboard=dashboard_url,
                    pid=project['_id'],
                    name=file_record['path'],
                    version=version
                ))
        except KeyError:
            pass

    return urls

def generate_wiki_urls(project, parent_id=None):
    
    urls = []

    dashboard_url = _get_dashboard_url(project, parent_id)

    if 'wiki_pages_current' not in project:
        return urls

    for page_name, page_id in project['wiki_pages_current'].items():
        page_record = database['nodewikipage'].find_one({'_id' : ObjectId(page_id)})
        if not page_record:
            continue
        current_url = '{dashboard}wiki/{name}'.format(
            dashboard=dashboard_url,
            pid=project['_id'],
            name=page_name
        )
        urls.append(current_url)
        for version in range(1, page_record['version'] + 1):
            urls.append('{current}/compare/{version}'.format(
                current=current_url,
                version=version
            ))

    return urls

def generate_project_urls(pid, is_project=True):
    
    project = database['node'].find_one({'_id' : pid})
    if not project:
        return []

    parent_id = None
    if not is_project:
        try:
            parent_id = project['_b_node_parent']
        except KeyError:
            print 'oh shit', project['_id'], project.keys()
            pass

    urls = generate_basic_urls(project, parent_id=parent_id) + \
        generate_wiki_urls(project, parent_id=parent_id) + \
        generate_file_urls(project, parent_id=parent_id)

    return urls

def generate_projects_urls(public=True):

    pids = database['node'].find({
        'is_public' : public,
        'category' : 'project',
    })

    project_urls = sum(
        [generate_project_urls(pid['_id']) for pid in pids],
        []
    )

    nids = database['node'].find({
        'is_public' : public,
        'category' : {'$ne' : 'project'},
    })

    node_urls = sum(
        [generate_project_urls(nid['_id'], is_project=False) for nid in nids],
        []
    )

    return project_urls + node_urls

def generate_profile_urls():
    
    users = database['user'].find()
    return ['/profile/{uid}'.format(uid=user['_id']) for user in users]

def generate_static_urls():
    return [
        '/faq',
        '/explore',
        '/explore/activity',
        '/getting-started',
    ]
