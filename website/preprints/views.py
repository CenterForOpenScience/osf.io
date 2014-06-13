import httplib as http
from flask import request
from modularodm.query.querydialect import DefaultQueryDialect as Q
from framework import must_be_logged_in, redirect
from framework.analytics.piwik import PiwikClient
from website import settings
import website.addons.osffiles.views as osffiles_views
from website.project import new_node, Node
from website.project.decorators import must_be_valid_project
from os.path import splitext

import website.views as website_views


# TODO: this is mostly duplicated code from discovery/views.py
def preprint_activity():

    popular_preprints = []
    hits = {}

    if settings.PIWIK_HOST:
        client = PiwikClient(
            url=settings.PIWIK_HOST,
            auth_token=settings.PIWIK_ADMIN_TOKEN,
            site_id=settings.PIWIK_SITE_ID,
            period='week',
            date='today',
        )
        popular_project_ids = [
            x for x in client.custom_variables if x.label == 'Project ID'
        ][0].values

        # TODO: these sorts of things should be refactored out
        for nid in popular_project_ids:
            node = Node.load(nid.value)
            if node is None:
                continue
            if node.is_public and not node.is_registration and node['category'] == 'preprint':
                if len(popular_preprints) < 10:
                    popular_preprints.append(node)
            if len(popular_preprints) >= 10:
                break

        hits = {
            x.value: {
                'hits': x.actions,
                'visits': x.visits
            } for x in popular_project_ids
        }

    # Projects

    recent_query = (
        Q('category', 'eq', 'project') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )

    # Temporary bug fix: Skip projects with empty contributor lists
    # Todo: Fix underlying bug and remove this selector
    recent_query = recent_query & Q('contributors', 'ne', [])

    recent_preprints_query = (
        Q('category', 'eq', 'preprint') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )
    recent_preprints_query = recent_preprints_query & Q('contributors', 'ne', [])

    recent_preprints = Node.find(
        recent_preprints_query
    ).sort(
        '-date_created'
    ).limit(10)

    return {
        'recent_preprints': recent_preprints,
        'popular_preprints': popular_preprints,
        'hits': hits,
    }

# def preprint_activity(**kwargs):
#     return discovery_views.activity(**kwargs)

@must_be_logged_in
def preprint_new(**kwargs):
    return {}, http.OK

@must_be_logged_in
def post_preprint_new(**kwargs):
    # todo: validation that file is pdf
    # todo: add error handling

    auth = kwargs['auth']
    file = request.files.get('file')
    # todo: should this leave it as unicode? Thinking about, e.g. mathematical symbols in titles
    node_title = splitext(file.filename)[0]
    # node_title = str(splitext(file.filename)[0])

    # creates private project to house the preprint component
    project = new_node('project',
                       node_title,
                       auth.user,
                       description='Automatically generated as a preprint for ' + node_title)
    project.set_privacy('private', auth=auth)

    # creates public component to house the preprint file
    preprint_component = new_node('preprint',
                                  node_title + " (Preprint)",
                                  auth.user,
                                  project=project)
    preprint_component.set_privacy('public', auth=auth)

    # commits to database upon successful creation of project and component
    project.save()
    preprint_component.save()

    # adds file to new component
    upload_preprint(project=project,
                    node=preprint_component,
                    **kwargs)

    return redirect(preprint_component.url+'preprint/')

@must_be_valid_project
def upload_preprint(**kwargs):
    rv = osffiles_views.upload_file_public(filename="preprint.pdf", **kwargs)
    node = kwargs['node'] or kwargs['project']
    return rv

def preprint_dashboard(**kwargs):
    return website_views.dashboard(**kwargs)

@must_be_logged_in
def get_preprint_dashboard_nodes(auth, **kwargs):
    user = auth.user

    contributed = user.node__contributed

    preprints = contributed.find(
        Q('category', 'eq', 'preprint') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False)
    ) # There's a lot of boilerplate here. we should fix that

    # TODO: I don't like importing _*. What should I do with this?
    return website_views._render_nodes(list(preprints))