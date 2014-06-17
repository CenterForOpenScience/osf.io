import httplib as http
from flask import request
from modularodm.query.querydialect import DefaultQueryDialect as Q
from framework import must_be_logged_in, redirect
from framework.analytics.piwik import PiwikClient
from framework.exceptions import HTTPError
from website import settings
import website.addons.osffiles.views as osffiles_views
import website.project.views as project_views
from website.project import new_node, Node
from os.path import splitext
from website.project.decorators import must_be_valid_project, must_be_contributor_or_public, must_have_addon
from website.util import rubeus

import website.views as website_views

# N.B.: Several of these view functions, marked below simply call other view functions. We want the same
# data, but rendered in a different template. Limitations of the current routing system require the view
# functions to have different names if they use the same renderer, hence this suboptimal solution.
# These functions should be unnecessary once the site has more dynamic behavior: the page can simply get the same
# data via the API.

# Many of the view functions called are decorated. Decorating these
# functions again may cause unpredictable behavior.


# This calls a decorated function. Decorating it may cause confusing behavior.
def preprint_dashboard(**kwargs):
    return website_views.dashboard(**kwargs)

# This calls a decorated function. Decorating it may cause confusing behavior.


def view_project_as_preprint(**kwargs):
    return project_views.node.view_project(**kwargs)

# This calls a decorated function. Decorating it may cause confusing behavior.


def upload_preprint(**kwargs):
    """This function uploads the file in `request` to an existing component. First it renames that file `preprint.pdf`."""

    request.files['file'].filename = unicode("preprint.pdf")
    rv = osffiles_views.upload_file_public(**kwargs)
    return rv

# This calls upload_preprint, which calls a decorated function. Decorating
# it may cause confusing behavior.


@must_be_logged_in
def post_preprint_new(**kwargs):
    """This function is the endpoint for the url where the user can create a new preprint project.
    It creates a new private project named with the name of the uploaded pdf.
    This project is given a public component named with the name of the uploaded pdf with ' (Preprint)'
    as a suffix.
    Finally, this component contains the uploaded pdf as an OsfFile with the name 'preprint.pdf'."""

    # todo: validation that file is pdf
    # todo: add error handling

    auth = kwargs['auth']
    file = request.files.get('file')
    # todo: should this leave it as unicode? Thinking about, e.g. mathematical
    # symbols in titles
    node_title = splitext(file.filename)[0]

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

    return redirect(preprint_component.url + 'preprint/')


@must_be_logged_in
def get_preprint_dashboard_nodes(auth, **kwargs):
    """This function queries the database for and renders the nodes for the preprint dashboard"""
    user = auth.user

    contributed = user.node__contributed

    preprints = contributed.find(
        Q('category', 'eq', 'preprint') &
        Q('is_deleted', 'eq', False) &
        Q('is_registration', 'eq', False)
    )  # There's a lot of boilerplate here. we should fix that

    # TODO: I don't like importing _*. What should I do with this?
    return website_views._render_nodes(list(preprints))


@must_be_valid_project  # returns project
@must_be_contributor_or_public  # returns user, project
@must_have_addon('osffiles', 'node')
def preprint_files(**kwargs):
    node = kwargs['node'] or kwargs['project']
    auth = kwargs['auth']

    files = rubeus.to_hgrid(node, auth)[0]['children']
    rv = {'supplements': []}
    for f in files:
        if f['name'] == 'preprint.pdf':
            rv['pdf'] = f
            rv['pdf']['versions'] = osffiles_views.file_versions('preprint.pdf', node)
            # rv['pdf']['render_url'] = f.render_url(node)
        else:
            rv['supplements'].append(f)
    return rv


@must_be_logged_in
def preprint_new(**kwargs):
    """This is the view function for a page that serves a dynamically-generated widget that allows the user to
    create a new preprint project."""
    return {}, http.OK

base_recent_preprint_query = (
        Q('category', 'eq', 'preprint') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    ) # TODO: refactor to remove boilerplate shared with other activity-getting queries
# Temporary bug fix: Skip projects with empty contributor lists
# Todo: Fix underlying bug and remove this selector
base_recent_preprint_query = base_recent_preprint_query & Q('contributors', 'ne', [])


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

    recent_preprints_query = (
        Q('category', 'eq', 'preprint') &
        Q('is_public', 'eq', True) &
        Q('is_deleted', 'eq', False)
    )  # TODO: refactor to remove boilerplate shared with other activity-getting queries
    # Temporary bug fix: Skip projects with empty contributor lists
    # Todo: Fix underlying bug and remove this selector
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

preprint_disciplines = {
    'Humanities': [
        'Linguistics',
        'Philosophy',
        'History'
    ],
    'Social Sciences': [
        'Economics',
        'Political Science',
        'Psychology'
    ],
    'Natural Sciences': [
        'Physics',
        'Chemistry',
        'Biology'
    ],
    'Formal Sciences': [
        'Mathematics',
        'Statistics',
        'Logic'
    ],
    'Professional and Applied Sciences': [
        'Computer Science',
        'Law',
        'Healthcare Science'
    ]}

disciplines_flattened = preprint_disciplines.keys() +\
    [d for dlist in preprint_disciplines.values() for d in dlist]

def valid_discipline(name):
    formatted_disciplines = [d.lower().replace(" ", "-") for d in disciplines_flattened]
    return str(name) in formatted_disciplines

def disciplines():
    return {
        'disciplines': preprint_disciplines}

def preprint_discipline_new(discipline=None,**kwargs):
    if not discipline:
        raise HTTPError("")
    if not valid_discipline(discipline):
        raise HTTPError("")

    discipline_query = (
        base_recent_preprint_query &
        Q('tags', 'eq', discipline.replace("-", " "))
    )

    recent_preprints = Node.find(
        discipline_query
    ).sort(
        '-date_created'
    ).limit(10)

    return {
        'recent_preprints': recent_preprints,
        'discipline': discipline.replace('-', ' ').title(),
        }


def preprint_discipline_popular():
    raise NotImplementedError